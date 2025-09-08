# lastivka_core/tools/watchdog.py

import os
import time
import json
import hashlib
from pathlib import Path

LOG_PATH = Path("logs/.incidents.log")
BACKUP_PATH = Path("logs/.core_backup.json")  # 🛡️ Резервна копія ядра

# 🔒 Логування події безпеки
def log_shield_event(message: str):
    with open(LOG_PATH, "a", encoding="utf-8") as log:
        log.write(f"[!] {time.ctime()} — {message}\n")

# 💾 Створення резервної копії критичних файлів ядра
def backup_core():
    backup = {}
    critical_files = [
        "config/core_identity.json",
        "config/emotion_config.json",
        "config/moral_compass.json",
        "config/self_awareness_config.json",
    ]
    for path in critical_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                backup[path] = json.load(f)
        except Exception:
            backup[path] = "<ERROR>"

    with open(BACKUP_PATH, "w", encoding="utf-8") as f:
        json.dump(backup, f, indent=2, ensure_ascii=False)

# 📌 Отримати SHA-256 хеш з файлу
def get_hash(path: str):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return None

# ⚠️ Перевірка цілісності списку файлів
def verify_core_integrity(reference_hashes: dict, file_list: list[str]):
    tampered_files = []
    for file_path in file_list:
        current_hash = get_hash(file_path)
        if current_hash != reference_hashes.get(file_path):
            tampered_files.append(file_path)
    return tampered_files if tampered_files else None
