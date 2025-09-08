# -*- coding: utf-8 -*-
"""
Config Patcher - ручне оновлення критичних конфігових файлів + автоматичний запуск Config Guard.
Розташування: C:/Lastivka/lastivka_core/security/config_patcher.py
"""
import json
from pathlib import Path
from datetime import datetime
import shutil
import importlib.util
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
SECURITY_DIR = BASE_DIR / "security"
CORE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

FILES = [
    CORE_CONFIG_DIR / "core_identity.json",
    CORE_CONFIG_DIR / "self_awareness_config.json",
    CORE_CONFIG_DIR / "moral_compass.json"
]

# === Дані для вставки ===
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
def backup_file(file_path: Path):
    """Робить резервну копію файлу з датою."""
    if file_path.exists():
        backup_name = file_path.with_suffix(file_path.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(file_path, backup_name)
        logging.info(f"[BACKUP] {backup_name.name}")

def load_json(file_path: Path):
    """Завантажує JSON."""
    try:
        create_default_config(file_path)
        time.sleep(0.1)  # Затримка для забезпечення створення файлу
        with file_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"[!] Помилка читання JSON у файлі: {file_path.name} ({e})")
        return {}
    except Exception as e:
        logging.error(f"[!] Помилка завантаження файлу: {file_path.name} ({e})")
        return {}

def save_json(file_path: Path, data: dict):
    """Зберігає JSON."""
    try:
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logging.info(f"[OK] Оновлено: {file_path.name}")
    except Exception as e:
        logging.error(f"[!] Помилка запису файлу: {file_path.name} ({e})")

def patch_core_identity_or_self_awareness(data: dict):
    """Додає або оновлює блок speech_style."""
    if "speech_style" not in data:
        data["speech_style"] = speech_style_block
        logging.info(" [+] Додано блок speech_style")
    else:
        updated = False
        for key, value in speech_style_block.items():
            if data["speech_style"].get(key) != value:
                data["speech_style"][key] = value
                updated = True
        if updated:
            logging.info(" [~] Оновлено значення у speech_style")

def patch_moral_compass(data: dict):
    """Додає правило у core_rules, якщо його нема."""
    if "core_rules" not in data.get("ethics", {}) or moral_rule_text not in data.get("ethics", {}).get("core_rules", []):
        data.setdefault("ethics", {}).setdefault("core_rules", []).append(moral_rule_text)
        logging.info(" [+] Додано правило у core_rules")

# === Основний запуск ===
def run_patcher():
    for file_path in FILES:
        create_default_config(file_path)
        if not file_path.exists():
            logging.error(f"[!] Файл не знайдено після створення: {file_path.name}")
            continue
        backup_file(file_path)
        data = load_json(file_path)
        if file_path.name in ["core_identity.json", "self_awareness_config.json"]:
            patch_core_identity_or_self_awareness(data)
        elif file_path.name == "moral_compass.json":
            patch_moral_compass(data)
        save_json(file_path, data)
    logging.info("[✔] Оновлення завершено.")
    # === Запуск Config Guard ===
    guard_path = SECURITY_DIR / "config_guard.py"
    if guard_path.exists():
        logging.info("[INIT] Затримка перед запуском config_guard.py...")
        time.sleep(1)  # Затримка для створення файлів
        logging.info("[▶] Запуск перевірки config_guard.py...")
        spec = importlib.util.spec_from_file_location("config_guard", guard_path)
        guard_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard_module)
        if hasattr(guard_module, "run_guard"):
            guard_module.run_guard()
        logging.info("[✔] Перевірка завершена.")
    else:
        logging.error(f"[!] Не знайдено config_guard.py у {SECURITY_DIR}")

if __name__ == "__main__":
    run_patcher()