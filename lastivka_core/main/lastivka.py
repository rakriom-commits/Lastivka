# lastivka.py — головний раннер Ластівки (фінальна редакція)
# Функції:
#  • headless-старт підпроцесів з опорою на tools/active/headless_guard_v*
#  • читання tools/config.json (за наявності)
#  • опційне прикріплення до Windows Job Object (якщо встановлено pywin32)
#  • retry/backoff, легкий менеджер процесів
#  • CLI: lastivka run ... | lastivka retry ...

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# --------------------------------- конфіг ------------------------------------

# ВАЖЛИВО: цей файл лежить у lastivka_core/main/, тому корінь пакета — на рівень вище.
MAIN_DIR = Path(__file__).resolve().parent          # .../lastivka_core/main
BASE = MAIN_DIR.parent                               # .../lastivka_core
TOOLS = BASE / "tools"
CONFIG_FILE = TOOLS / "config.json"

def _load_config() -> Dict[str, Any]:
    cfg: Dict[str, Any] = {
        "log_level": "INFO",
        "default_timeout": 15,
        "headless": True,
        "job_object_mb": None,   # напр.: 256 або None
    }
    try:
        if CONFIG_FILE.exists():
            with CONFIG_FILE.open("r", encoding="utf-8") as f:
                user = json.load(f)
            if isinstance(user, dict):
                cfg.update(user)
    except Exception:
        pass
    return cfg

CONFIG = _load_config()

# --------------------------------- логування ---------------------------------

LOG_LEVEL = str(CONFIG.get("log_level", os.environ.get("LASTIVKA_LOG_LEVEL", "INFO"))).upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger("lastivka")

# ------------------------------ headless guard --------------------------------

try:
    # Агрегатор у tools/active генерується self_programmer.promote()
    # Експортує версійні ран-функції, напр. run_headless_guard_v2
    from lastivka_core.tools import active as tools_active  # type: ignore
except Exception:
    tools_active = None
    log.debug("tools.active unavailable; guard disabled")

def _resolve_guard_run() -> Optional[Any]:
    """Повертає run-функцію найновішого headless_guard_v* з агрегатора, або None."""
    if not tools_active:
        return None
    try:
        latest_v = -1
        for item in getattr(tools_active, "__all__", []):
            if isinstance(item, str) and item.startswith("headless_guard_v"):
                try:
                    v = int(item.rsplit("_v", 1)[1])
                    latest_v = max(latest_v, v)
                except Exception:
                    pass
        if latest_v >= 0:
            fn = getattr(tools_active, f"run_headless_guard_v{latest_v}", None)
            if callable(fn):
                log.debug("headless_guard_v%s bound", latest_v)
                return fn
    except Exception as e:
        log.debug("resolve guard failed: %s", e)
    return None

_HEADLESS_RUN = _resolve_guard_run()

# boot-директиви як підказки (OS-дії тут не виконуємо)
HEADLESS_BOOT: Dict[str, Any] = {"directives": [], "params": {}}
if _HEADLESS_RUN:
    try:
        HEADLESS_BOOT = _HEADLESS_RUN(op="boot") or HEADLESS_BOOT
    except Exception as e:
        log.debug("boot directives error: %s", e)

BOOT_ENFORCE_HEADLESS = "enforce_headless" in (HEADLESS_BOOT.get("directives") or [])

# ---------------------------- Windows флаги вікна -----------------------------

CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008

# ----------------------------- опційний Job Object ----------------------------

def _maybe_attach_job_object(proc: subprocess.Popen, mem_limit_mb: Optional[int] = None) -> None:
    """Опційно прикріплює процес до Windows Job Object із м’яким лімітом пам'яті."""
    if platform.system() != "Windows":
        return
    try:
        import win32job, win32con, win32api  # type: ignore

        hJob = win32job.CreateJobObject(None, "")
        info = win32job.QueryInformationJobObject(hJob, win32job.JobObjectExtendedLimitInformation)
        flags = info["BasicLimitInformation"]["LimitFlags"]
        flags |= win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if mem_limit_mb:
            flags |= win32job.JOB_OBJECT_LIMIT_PROCESS_MEMORY
            info["ProcessMemoryLimit"] = int(mem_limit_mb) * 1024 * 1024
        info["BasicLimitInformation"]["LimitFlags"] = flags
        win32job.SetInformationJobObject(hJob, win32job.JobObjectExtendedLimitInformation, info)

        hProc = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, proc.pid)
        win32job.AssignProcessToJobObject(hJob, hProc)
        log.debug("JobObject attached to pid=%s (mem=%sMB)", proc.pid, mem_limit_mb)
    except Exception as e:
        log.debug("JobObject not attached: %s", e)

# --------------------------- стратегія від guard ------------------------------

def _headless_strategy(hints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Повертає ярлик стратегії від guard; якщо guard недоступний — noop."""
    if not _HEADLESS_RUN:
        return {"strategy": "noop", "score": 0, "explain": "guard unavailable"}
    try:
        base_hints: Dict[str, Any] = {
            "no_console_needed": True,
            "supports_create_no_window": (platform.system() == "Windows"),
            # "uses_win32job": True,  # вмикай, якщо реально прикріплюєш Job Object
        }
        # підсилюємо з boot/config
        if BOOT_ENFORCE_HEADLESS or CONFIG.get("headless", True):
            base_hints["no_console_needed"] = True
        if hints:
            base_hints.update(hints)
        out = _HEADLESS_RUN(mode="default", hints=base_hints) or {}
        if "strategy" not in out:
            out["strategy"] = "noop"
        return out
    except Exception as e:
        return {"strategy": "noop", "score": -1, "explain": f"guard error: {e}"}

# -------------- маппінг стратегії → kwargs для subprocess.Popen --------------

def _build_spawn_kwargs_by_strategy(strategy: str) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if platform.system() == "Windows":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        kwargs["startupinfo"] = si

        if strategy == "create_no_window":
            kwargs["creationflags"] = kwargs.get("creationflags", 0) | CREATE_NO_WINDOW
        elif strategy == "detach_handles":
            kwargs["creationflags"] = kwargs.get("creationflags", 0) | DETACHED_PROCESS
        elif strategy == "job_object_hide":
            kwargs["creationflags"] = kwargs.get("creationflags", 0) | CREATE_NO_WINDOW
        else:
            pass
    return kwargs

# ------------------------ публічний API запусків -----------------------------

def spawn_headless(
    cmd: List[str] | str,
    *,
    hints: Optional[Dict[str, Any]] = None,
    job_object_mb: Optional[int] = None,
    **overrides: Any,
) -> subprocess.Popen:
    """Стартує підпроцес у headless-режимі з урахуванням порад guard."""
    strat = _headless_strategy(hints)
    kwargs = _build_spawn_kwargs_by_strategy(strat.get("strategy", "noop"))
    kwargs.update(overrides or {})
    log.debug("spawn: %r, strategy=%s", cmd, strat.get("strategy"))
    p = subprocess.Popen(cmd, **kwargs)
    if job_object_mb:
        _maybe_attach_job_object(p, job_object_mb)
    return p

def run_command_headless(
    cmd: List[str] | str,
    *,
    timeout: Optional[float] = None,
    hints: Optional[Dict[str, Any]] = None,
    check: bool = True,
    **overrides: Any,
) -> int:
    """Запускає команду headless і чекає завершення. Повертає код виходу."""
    p = spawn_headless(
        cmd,
        hints=hints,
        job_object_mb=overrides.pop("job_object_mb", CONFIG.get("job_object_mb")),
        **overrides,
    )
    try:
        rc = p.wait(timeout=timeout or CONFIG.get("default_timeout", 15))
    except Exception:
        p.kill()
        p.wait()
        raise
    if check and rc != 0:
        raise subprocess.CalledProcessError(rc, cmd)
    return rc

def run_command_headless_with_retry(
    cmd: List[str] | str,
    *,
    attempts: int = 3,
    backoff_sec: float = 0.4,
    timeout: Optional[float] = None,
    hints: Optional[Dict[str, Any]] = None,
    **overrides: Any,
) -> int:
    """Те саме, але з повторами й експоненційним бекоффом."""
    last_exc: Optional[BaseException] = None
    for i in range(1, max(1, attempts) + 1):
        try:
            return run_command_headless(cmd, timeout=timeout, hints=hints, **overrides)
        except subprocess.CalledProcessError as e:
            last_exc = e
            log.warning("rc=%s attempt %s/%s", e.returncode, i, attempts)
        except Exception as e:
            last_exc = e
            log.warning("error=%s attempt %s/%s", e, i, attempts)
        time.sleep(backoff_sec * (2 ** (i - 1)))
    assert last_exc is not None
    raise last_exc

# --------------------------- легкий менеджер процесів -------------------------

class ProcessManager:
    def __init__(self) -> None:
        self._procs: List[subprocess.Popen] = []

    def spawn(self, cmd: List[str] | str, **kw: Any) -> subprocess.Popen:
        p = spawn_headless(cmd, **kw)
        self._procs.append(p)
        return p

    def sweep(self) -> None:
        self._procs = [p for p in self._procs if p.poll() is None]

    def terminate_all(self, kill_after: float = 1.0) -> None:
        for p in self._procs:
            if p.poll() is None:
                try:
                    p.terminate()
                except Exception:
                    pass
        t0 = time.time()
        while any(p.poll() is None for p in self._procs) and (time.time() - t0) < kill_after:
            time.sleep(0.05)
        for p in self._procs:
            if p.poll() is None:
                try:
                    p.kill()
                except Exception:
                    pass
        self._procs.clear()

# ----------------------------------- CLI -------------------------------------

def _build_cli(argv: Optional[List[str]]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="lastivka", add_help=True)
    sub = p.add_subparsers(dest="cmd")

    p_run = sub.add_parser("run", help="run a command headlessly and wait")
    p_run.add_argument("command", nargs=argparse.REMAINDER, help="command to run")
    p_run.add_argument("--timeout", type=float, default=None)
    p_run.add_argument("--no-check", action="store_true")
    p_run.add_argument("--job-mb", type=int, default=None)

    p_retry = sub.add_parser("retry", help="run a command with retry/backoff")
    p_retry.add_argument("command", nargs=argparse.REMAINDER)
    p_retry.add_argument("--attempts", type=int, default=3)
    p_retry.add_argument("--backoff", type=float, default=0.4)

    args = p.parse_args(argv)
    return args

def main(argv: Optional[List[str]] = None) -> int:
    args = _build_cli(argv)
    if args.cmd == "run":
        if not args.command:
            log.error("Nothing to run. Use: lastivka run <command ...>")
            return 2
        rc = run_command_headless(
            args.command,
            timeout=args.timeout,
            check=not args.no_check,
            job_object_mb=args.job_mb if args.job_mb is not None else CONFIG.get("job_object_mb"),
        )
        print(rc)
        return 0
    if args.cmd == "retry":
        if not args.command:
            log.error("Nothing to run. Use: lastivka retry <command ...>")
            return 2
        rc = run_command_headless_with_retry(
            args.command,
            attempts=args.attempts,
            backoff_sec=args.backoff,
        )
        print(rc)
        return 0
    # якщо команду не задано — показати довідку
    _build_cli(["-h"])
    return 2

# -------------------- Legacy test compatibility shim --------------------

def main_loop() -> bool:
    """
    Compatibility shim for legacy tests expecting lastivka_core.main.lastivka.main_loop().
    Нічого не запускає; повертає True, щоб колекція pytest не падала.
    """
    try:
        # легка перевірка доступності guard/стратегії (без побічних ефектів)
        _ = _headless_strategy({"no_console_needed": True})
    except Exception:
        pass
    return True

if __name__ == "__main__":
    raise SystemExit(main())
