# tools/file_watcher.py

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))  # Додаємо lastivka_core до системного шляху

import time
import hashlib
import shutil
from datetime import datetime

from tools.speech_utils import speak
from tools.emotion_engine import set_emotion

WATCHED_FILES = [
    Path("config/core_identity.json"),
    Path("config/moral_compass.json"),
    Path("config/emotion_config.json"),
    Path("logs/memory_store.json"),
    Path("main/lastivka.py")
]

HASH_LOG = {}
CHECK_INTERVAL = 15  # інтервал перевірки у секундах

def compute_file_hash(file_path):
    try:
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return None

def init_hash_log():
    for file in WATCHED_FILES:
        HASH_LOG[file] = compute_file_hash(file)

def backup_file(file):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = file.parent / f"{file.stem}_backup_{timestamp}{file.suffix}"
    try:
        shutil.copy(file, backup_path)
        print(f"[✔] Файл резервного копіювання створено: {backup_path.name}")
    except Exception as e:
        print(f"[❌] Помилка при створенні резервної копії: {e}")

def handle_change(file):
    print(f"[⚠] Зміна виявлена у файлі {file.name}. Створюємо резервну копію...")
    if file.name == "memory_store.json":
        set_emotion("подив")
        speak("Увага. Було змінено памʼять. Чи слід проаналізувати?")
    else:
        set_emotion("тривога")
        speak(f"Було змінено файл {file.name}. Будь ласка, перевір справність.")

def monitor_files(on_change_callback=handle_change):
    init_hash_log()
    print("[🔍] FileWatcher запущено. Стежимо за конфігураціями...")
    while True:
        for file in WATCHED_FILES:
            new_hash = compute_file_hash(file)
            if not new_hash:
                continue
            if new_hash != HASH_LOG.get(file):
                print(f"[🌀] Виявлено зміну у файлі: {file.name}")
                HASH_LOG[file] = new_hash
                backup_file(file)
                on_change_callback(file)
        time.sleep(CHECK_INTERVAL)

# Самостійний запуск
if __name__ == "__main__":
    monitor_files()
