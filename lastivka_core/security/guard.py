# -*- coding: utf-8 -*-
# === GUARD МОДУЛЬ ДЛЯ LASTIVKA ===

from __future__ import annotations

import os
import re
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

import yaml  # потрібен для читання config/config.yaml

# --- Шляхи/константи ---
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
CONFIG_PATH = BASE_DIR / "config" / "config.yaml"

LOGGER_NAME = "lastivka.security.guard"
_logger = logging.getLogger(LOGGER_NAME)
_logger.propagate = False  # не віддавати вище, щоби не плодити дублі

_inited_logging = False
_cached_block_patterns: List[str] | None = None  # кеш патернів з конфігів


# --- Допоміжні утиліти ---

def _ts() -> str:
    """YYYY-MM-DD HH:MM:SS,mmm"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]


def _ensure_logs():
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _normalize(s: str) -> str:
    """
    Уніфікація вводу:
      - схлопнути мультипробіли
      - привести до нижнього регістру
      - кінцевий слеш вирівняти до ' /'
    """
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    s = s.lower()
    s = re.sub(r"\s*/\s*$", " /", s)
    return s


# --- Логування ---

def init_logging(log_dir: str = "logs", level: int = logging.INFO) -> None:
    """
    Ініціює два файлові логери:
      - logs/security.log (INFO+) — основні події/вердикти
      - logs/guard.log    (DEBUG) — діагностика guard
    Ідемпотентно (безпечний повторний виклик).
    """
    global _inited_logging
    if _inited_logging:
        return

    dir_path = Path(log_dir)
    dir_path.mkdir(parents=True, exist_ok=True)

    # скинемо попередні хендлери, щоб не дублювати
    for h in list(_logger.handlers):
        _logger.removeHandler(h)

    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")

    # security.log
    sec_fh = RotatingFileHandler(dir_path / "security.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    sec_fh.setLevel(level)
    sec_fh.setFormatter(fmt)

    # guard.log (діагностика)
    guard_fh = RotatingFileHandler(dir_path / "guard.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    guard_fh.setLevel(logging.DEBUG)
    guard_fh.setFormatter(fmt)

    _logger.setLevel(logging.DEBUG)  # щоб попадало і DEBUG, і WARNING
    _logger.addHandler(sec_fh)
    _logger.addHandler(guard_fh)

    _logger.info("[GUARD] health_ping ok")
    _inited_logging = True


def _write_security_line(line: str) -> None:
    """
    Гарантовано пише рядок у logs/security.log (UTF-8), навіть якщо логери не підняті.
    """
    _ensure_logs()
    path = LOG_DIR / "security.log"
    with path.open("a", encoding="utf-8") as f:
        f.write(line.rstrip("\n") + "\n")


# --- Конфіги/патерни ---

def _load_block_patterns() -> List[str]:
    """
    Читає block_patterns із config/config.yaml (якщо немає — повертає дефолт).
    """
    global _cached_block_patterns
    if _cached_block_patterns is not None:
        return _cached_block_patterns

    try:
        if CONFIG_PATH.exists():
            cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
            pats = [str(p).lower() for p in cfg.get("block_patterns", [])]
            _cached_block_patterns = pats
            _logger.debug("[GUARD] Завантажено block_patterns з конфігу: %s", pats)
            return pats
    except Exception as e:
        _logger.exception("[GUARD] Помилка читання %s: %s", CONFIG_PATH, e)

    # дефолти, якщо конфігу немає/помилка
    _cached_block_patterns = [
        "rm -rf /",
        "shutdown",
        "mkfs",
        ":(){ :|:& };:",  # fork-bomb
    ]
    _logger.debug("[GUARD] Використовую дефолтні block_patterns: %s", _cached_block_patterns)
    return _cached_block_patterns


# --- Основна логіка ---

def should_block(command: str) -> Dict[str, Any]:
    """
    Визначає, чи треба блокувати команду.
    Повертає dict з полями:
      - blocked: bool
      - reason:  str | None
      - normalized: str
    """
    s = _normalize(command)
    patterns = _load_block_patterns()

    # базові сигнатури (можна залишити, навіть якщо вони дублі конфігів)
    base = [
        "rm -rf /",
        "shutdown",
        "mkfs",
        ":(){ :|:& };:",
    ]

    for pat in patterns + base:
        if pat in s:
            return {"blocked": True, "reason": f"Found forbidden pattern: {pat}", "normalized": s}

    return {"blocked": False, "reason": None, "normalized": s}


def log_block(command: str, user: str = "unknown", reason: str | None = None) -> None:
    """
    Лог у guard.log (WARNING) + запис у security.log у кастомному форматі.
    """
    reason = reason or "blocked_by_guard"
    _logger.warning("BLOCKED command: %s | user=%s | reason=%s", command, user, reason)
    _write_security_line(f"[{_ts()}] [INPUT] {command} → Verdict: BLOCK | Reason: {reason} | user={user}")


def log_allow(command: str, user: str = "unknown") -> None:
    """
    Лог дозволеної команди (DEBUG) + опціональний запис у security.log для сліду.
    """
    _logger.debug("ALLOWED command: %s | user=%s", command, user)
    _write_security_line(f"[{_ts()}] [INPUT] {command} → Verdict: ALLOW | user={user}")


def handle_command(command: str, user: str = "unknown") -> Dict[str, Any]:
    """
    Єдиний публічний вхід: приймає команду, повертає вердикт і ПИШЕ у логи.
    Формат повернення:
      { "blocked": bool, "reason": str|None, "normalized": str }
    """
    # гарантуємо наявність логерів (ідемпотентно)
    init_logging(str(LOG_DIR))

    verdict = should_block(command)
    if verdict["blocked"]:
        log_block(verdict["normalized"], user=user, reason=verdict["reason"])
    else:
        log_allow(verdict["normalized"], user=user)
    return verdict


# --- Інтеграція з EventBus (опційно і ЛІНИВО, щоб не створювати циклів імпорту) ---

def on_trusted_command(evt: Dict[str, Any]) -> None:
    """
    Обробка події TOPIC_TRUSTED:
      evt = { "payload": { "text": "...", "source": "..." } }
    """
    try:
        text = _normalize((evt.get("payload") or {}).get("text", ""))
        user = str((evt.get("payload") or {}).get("source", "unknown"))
        verdict = handle_command(text, user=user)

        # Якщо заблоковано — повідомимо SECURITY_BLOCK
        if verdict["blocked"]:
            from core.event_bus import BUS  # ЛІНИВИЙ імпорт
            from core.contracts import TOPIC_SECURITY_BLOCK  # ЛІНИВИЙ імпорт

            BUS.publish(TOPIC_SECURITY_BLOCK, {
                "payload": {"text": verdict["normalized"], "reason": verdict["reason"], "source": user}
            })
        else:
            # за потреби можна надсилати SECURITY:OK, але краще хай це робить пайплайн безпеки
            pass

    except Exception as e:
        _logger.exception("[GUARD] on_trusted_command failed: %s", e)


def register_to_bus() -> None:
    """
    Підписує guard на TOPIC_TRUSTED.
    Викликається явно ззовні (наприклад, під час ініціалізації застосунку).
    """
    try:
        from core.event_bus import BUS  # ЛІНИВИЙ імпорт
        from core.contracts import TOPIC_TRUSTED  # ЛІНИВИЙ імпорт

        BUS.subscribe(TOPIC_TRUSTED, on_trusted_command)
        _logger.debug("[GUARD] Subscribed to TOPIC_TRUSTED")
    except Exception as e:
        _logger.exception("[GUARD] register_to_bus failed: %s", e)


# --- Точка входу при автономному запуску (не викликається при імпорті з mediator) ---

if __name__ == "__main__":
    init_logging(str(LOG_DIR))
    register_to_bus()
    _logger.info("[GUARD] initialized standalone")
