# C:\Lastivka\lastivka_core\core\gate.py
from __future__ import annotations
import argparse, hashlib, os, shutil, sys, time
from pathlib import Path

ROOT = Path(r"C:\Lastivka\lastivka_core")
OUTBOX = ROOT / "tools" / "outbox"
LOGS = ROOT / "logs"
ALLOW_FLAG = ROOT / "ALLOW_APPLY.flag"

OUTBOX.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)

def sha256(p: Path) -> str:
    if not p.exists() or not p.is_file():
        return "-"
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def parse_mode(argv=None):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    known, _ = ap.parse_known_args(argv)
    dry = known.dry_run or not known.apply
    app = bool(known.apply and ALLOW_FLAG.exists())
    # якщо просили --apply, але прапорця нема → примусово dry-run
    if known.apply and not ALLOW_FLAG.exists():
        dry, app = True, False
    return dry, app

def report_path(script_name: str) -> Path:
    ts = time.strftime("%Y%m%d_%H%M%S")
    return OUTBOX / f"{script_name}_{ts}.txt"

def manifest_path() -> Path:
    ts = time.strftime("%Y%m%d_%H%M%S")
    m = LOGS / f"manifest_{ts}.csv"
    if not m.exists():
        m.write_text("timestamp,script,action,path_from,path_to,size,sha256,status\n", encoding="utf-8")
    return m

def log_change(script: str, action: str, src: Path, dst: Path|None, status: str, mf: Path):
    ts = time.strftime("%Y%m%d_%H%M%S")
    p = dst if dst else src
    size = p.stat().st_size if p.exists() and p.is_file() else 0
    mf.open("a", encoding="utf-8").write(f"{ts},{script},{action},{src},{dst or ''},{size},{sha256(p)},{status}\n")

def apply_change(script: str, action: str, src: Path, dst: Path|None, dry: bool, mf: Path, w) -> None:
    # w — відкритий дескриптор звіту (report.txt)
    def write(line: str): w.write(line + "\n"); w.flush()
    write(f"[{script}] {('DRY' if dry else 'DO ')} {action} {src} -> {dst or ''}")
    if dry:
        log_change(script, action, src, dst, "SIMULATED", mf)
        return
    try:
        if action == "CREATE":
            src.parent.mkdir(parents=True, exist_ok=True)
            src.touch(exist_ok=True)
        elif action == "UPDATE":
            src.parent.mkdir(parents=True, exist_ok=True)
            # оновлення контенту виконують виклики, тут лише протокол
        elif action == "DELETE":
            if src.exists():
                if src.is_dir(): shutil.rmtree(src)
                else: src.unlink()
        elif action == "MOVE":
            assert dst is not None
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                if dst.exists(): shutil.rmtree(dst)
                shutil.move(str(src), str(dst))
            else:
                shutil.move(str(src), str(dst))
        elif action == "QUARANTINE":
            assert dst is not None
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
        else:
            raise ValueError(f"Unknown action {action}")
        log_change(script, action, src, dst, "APPLIED", mf)
    except Exception as e:
        write(f"[ERR] {action} failed: {e}")
        log_change(script, action, src, dst, "FAILED", mf)
        raise

def open_report(script_stem: str):
    rp = report_path(script_stem)
    return rp.open("a", encoding="utf-8"), rp
