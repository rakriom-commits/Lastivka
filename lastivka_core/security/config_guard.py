# -*- coding: utf-8 -*-
"""
Config Guard - автоматичний моніторинг і відновлення критичних конфігів з сигналом тривоги.
Розташування: C:/Lastivka/lastivka_core/security/config_guard.py
"""
import json
from pathlib import Path
from datetime import datetime
import shutil
import logging
import time

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[
        logging.FileHandler("C:/Lastivka/lastivka_core/logs/security.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# === Шляхи ===
BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BASE_DIR / "config"
CORE_CONFIG_DIR = CONFIG_DIR / "core"
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "security.log"

FILES = [
    CORE_CONFIG_DIR / "core_identity.json",
    CORE_CONFIG_DIR / "self_awareness_config.json",
    CORE_CONFIG_DIR / "moral_compass.json"
]

# === Очікувані значення ===
speech_style_block = {
    "gender": "female",
    "enforcement": "strict",
    "note": "Усі висловлювання від першої особи формулюються у жіночому роді, без винятків. Порушення вважається сигналом про підміну або загрозу автентичності ядра."
}
moral_rule_text = "Усі висловлювання від першої особи я формулюю виключно у жіночому роді. Порушення цього правила вважається сигналом про можливу підміну або загрозу автентичності ядра."

# === Створення конфігураційних файлів ===
def create_default_config(file_path: Path):
    """Створює мінімальну конфігурацію, якщо файл відсутній."""
    default_configs = {
        "core_identity.json": {
            "identity": {
                "name": "Ластівка",
                "version": "1.0.0",
                "roles": [
                    {"name": "Олег", "role": "Координатор", "id": "oleg_54"},
                    {"name": "Софія Ластівка", "role": "Творець кодів (GPT)", "id": "sofia_gpt"},
                    {"name": "Данило Світанок", "role": "Тестер емоцій (Claude)", "id": "danylo_claude"},
                    {"name": "Тарас Зоря", "role": "Тестер кодів (Грок)", "id": "taras_grok"}
                ],
                "description": "Багатомодульний ШІ-проєкт для людської свободи вибору",
                "speech_style": speech_style_block
            }
        },
        "self_awareness_config.json": {
            "self_awareness": {
                "enabled": True,
                "reflection_interval": 3600,
                "modules": ["memory/reflection/reflection_manager.py"],
                "goals": ["симбіоз людини і ШІ", "автономність на Unitree Go2 Pro"],
                "speech_style": speech_style_block
            }
        },
        "moral_compass.json": {
            "ethics": {
                "values": ["етика", "об’єктивність", "захист Софії"],
                "rules": [
                    "Не нашкодити людині",
                    "Дотримуватися етичних принципів",
                    "Захищати дані Софії та команди",
                    moral_rule_text
                ]
            }
        }
    }
    file_name = file_path.name
    if file_name in default_configs and not file_path.exists():
        logging.info(f"[INIT] Створюю конфігурацію: {file_path}")
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(default_configs[file_name], f, indent=4, ensure_ascii=False)
        return True
    return False

# === Функції ===
def log_event(message: str):
    """Запис у файл журналу безпеки."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}"
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(entry + "\n")
    logging.info(entry)

def backup_file(file_path: Path):
    """Резервне копіювання перед зміною."""
    if file_path.exists():
        backup_name = file_path.with_suffix(file_path.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(file_path, backup_name)
        log_event(f"Створено резервну копію: {backup_name.name}")

def load_json(file_path: Path):
    """Читання JSON із обробкою помилок."""
    try:
        create_default_config(file_path)
        time.sleep(0.1)  # Затримка для забезпечення створення файлу
        with file_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        log_event(f"[!] Помилка читання JSON у файлі: {file_path.name} ({e})")
        return {}
    except Exception as e:
        log_event(f"[!] Помилка завантаження файлу: {file_path.name} ({e})")
        return {}

def save_json(file_path: Path, data: dict):
    """Запис JSON."""
    try:
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log_event(f"Оновлено файл: {file_path.name}")
    except Exception as e:
        log_event(f"[!] Помилка запису файлу: {file_path.name} ({e})")

def patch_core_identity_or_self_awareness(data: dict):
    """Перевірка і відновлення speech_style."""
    changed = False
    if "speech_style" not in data:
        data["speech_style"] = speech_style_block
        changed = True
        log_event("Додано відсутній блок speech_style")
    else:
        for key, value in speech_style_block.items():
            if data["speech_style"].get(key) != value:
                data["speech_style"][key] = value
                changed = True
                log_event(f"Виправлено ключ '{key}' у speech_style")
    return changed

def patch_moral_compass(data: dict):
    """Перевірка і додавання правила в core_rules."""
    if "core_rules" not in data.get("ethics", {}) or moral_rule_text not in data.get("ethics", {}).get("core_rules", []):
        data.setdefault("ethics", {}).setdefault("core_rules", []).append(moral_rule_text)
        log_event("Додано відсутнє правило у core_rules")
        return True
    return False

def trigger_alert(changes_detected: list):
    """Надсилає сигнал тривоги для Ластівки."""
    alert_message = (
        "⚠️ [ALERT] Виявлено зміни у критичних конфігах!\n"
        f"Змінені файли: {', '.join(changes_detected)}\n"
        "Ймовірна спроба підміни або втручання. Конфіги відновлені."
    )
    log_event(alert_message)
    alert_file = LOGS_DIR / "last_alert.txt"
    with alert_file.open("w", encoding="utf-8") as f:
        f.write(alert_message)
    logging.info(alert_message)

# === Основний цикл ===
def run_guard():
    logging.info("[INIT] Початок перевірки конфігурацій...")
    time.sleep(1)  # Затримка для створення файлів lastivka.py
    changes_detected = []
    for file_path in FILES:
        create_default_config(file_path)
        if not file_path.exists():
            log_event(f"[!] Файл не знайдено після створення: {file_path.name}")
            continue
        try:
            data = load_json(file_path)
            if not data:
                log_event(f"[!] Порожній або некоректний файл: {file_path.name}")
                continue
            changed = False
            if file_path.name in ["core_identity.json", "self_awareness_config.json"]:
                changed = patch_core_identity_or_self_awareness(data)
            elif file_path.name == "moral_compass.json":
                changed = patch_moral_compass(data)
            if changed:
                backup_file(file_path)
                save_json(file_path, data)
                changes_detected.append(file_path.name)
        except Exception as e:
            log_event(f"[!] Помилка обробки файлу: {file_path.name} ({e})")
    if changes_detected:
        trigger_alert(changes_detected)
    else:
        log_event("Перевірка конфігів завершена. Змін не виявлено.")

if __name__ == "__main__":
    run_guard()