# -*- coding: utf-8 -*-
"""
Guardian Mode — аварійний режим безпечної поведінки Ластівки.
Три етапи:
1. Спроба виправлення проблеми security-модулем.
2. Якщо не вдалося — голосове попередження + світло/звук + лог.
3. 10-секундний відлік, після якого Safe Position Mode.
"""

import time
import logging
from pathlib import Path
import importlib.util

BASE_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = BASE_DIR / "logs"; LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("guardian_mode")
handler = logging.FileHandler(LOG_DIR / "guardian_mode.log", encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# ====== Конфіг ======
SECURITY_MODULE = BASE_DIR / "security" / "config_guard.py"

# Ці функції будуть передаватись із lastivka.py
say_safe = None
activate_alert_lights = None
safe_position = None

def attach_interfaces(say_func, lights_func, safe_pos_func):
    """Підключення зовнішніх функцій для озвучення, світлової сигналізації та переходу в безпечне положення."""
    global say_safe, activate_alert_lights, safe_position
    say_safe = say_func
    activate_alert_lights = lights_func
    safe_position = safe_pos_func

def run_security_fix():
    """Спроба виправити проблему через security-модуль."""
    if SECURITY_MODULE.exists():
        try:
            logger.info("Запуск security-модуля для виправлення...")
            spec = importlib.util.spec_from_file_location("config_guard", SECURITY_MODULE)
            guard_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(guard_module)
            if hasattr(guard_module, "run_guard"):
                result = guard_module.run_guard()
                logger.info(f"Security-модуль завершив роботу з результатом: {result}")
                return result
        except Exception as e:
            logger.error(f"Помилка під час запуску security-модуля: {e}")
    else:
        logger.warning(f"Security-модуль не знайдено: {SECURITY_MODULE}")
    return False

def guardian_emergency(reason: str = "Невідома помилка"):
    """Основний сценарій Guardian Mode."""
    logger.warning(f"[GUARDIAN MODE] Причина: {reason}")

    # 1. Спроба виправити
    if run_security_fix():
        logger.info("Проблему виправлено через security-модуль. Продовжую роботу.")
        return

    # 2. Попередження
    if say_safe:
        say_safe(f"Олег! У мене критична проблема: {reason}. Починаю відлік.")
    if activate_alert_lights:
        activate_alert_lights(True)
    logger.warning("Попередження видане. Початок відліку.")

    # 3. Відлік 10 секунд
    for i in range(10, 0, -1):
        if say_safe:
            say_safe(f"Залишилось {i} секунд.")
        time.sleep(1)

    # 4. Безпечне положення
    if say_safe:
        say_safe("Час вичерпано. Переходжу в безпечний режим.")
    if safe_position:
        safe_position()
    if activate_alert_lights:
        activate_alert_lights(False)
    logger.info("Guardian Mode завершено — Ластівка в безпечному положенні.")
