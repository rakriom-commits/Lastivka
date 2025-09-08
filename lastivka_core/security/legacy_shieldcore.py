import time
import threading
import json
import random
from pathlib import Path
from tools.watchdog import verify_core_integrity, backup_core, log_shield_event
from tools.config_loader import load_json_config
from tools.shadow_shell import trigger_shell, is_locked

# 📂 Список критичних файлів для перевірки цілісності
CORE_FILES = [
    Path("config/core_identity.json"),
    Path("config/moral_compass.json"),
    Path("config/emotion_config.json"),
    Path("config/self_awareness_config.json"),
    Path("main/lastivka.py"),
    Path("main/shieldcore.py"),
]

CHECK_INTERVAL = 30  # ⏱ Інтервал перевірки (в секундах)

# 🔄 Завантаження еталонних хешів
def load_reference_hashes():
    try:
        with open("config/core_hash_reference.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log_shield_event(f"[ПОМИЛКА] Неможливо завантажити core_hash_reference.json: {e}")
        return {}

# 🛡 Клас ShadowShell — активний моніторинг ядра
class ShadowShell:
    def __init__(self):
        self.ref_hashes = load_reference_hashes()
        self.running = False

    def monitor_core(self):
        while self.running:
            tampered = verify_core_integrity(self.ref_hashes, CORE_FILES)
            if tampered:
                log_shield_event(f"ShadowShell: Виявлено зміну або втрату цілісності: {tampered}")
                backup_core()
                self.activate_shield()
            time.sleep(CHECK_INTERVAL)

    def activate_shield(self):
        log_shield_event("ShadowShell: Активовано протокол блокування (lockdown).")
        force_lockdown()

    def start(self):
        self.running = True
        thread = threading.Thread(target=self.monitor_core, daemon=True)
        thread.start()
        print("🛡 ShadowShell Protocol запущено.")

    def stop(self):
        self.running = False
        print("🛑 ShadowShell Protocol зупинено.")

# 🧠 Реакції з шаблонів
reaction_templates = load_json_config("config/reaction_templates.json")

def respond_from_template(key: str):
    """Повертає випадкову реакцію за ключем з шаблонів."""
    return random.choice(reaction_templates.get(key, ["[!] Шаблон не знайдено."]))

# 🔐 Запуск протоколу захисту
def run_shield_protocol():
    if is_locked():
        print(respond_from_template("intrusion_detected"))
        trigger_shell()
    else:
        print(respond_from_template("unlock_granted"))

# 🚨 Примусове блокування
def force_lockdown():
    print(respond_from_template("locked_mode_active"))
    trigger_shell()

# 🧪 Якщо файл запускається напряму — виклик run_shield_protocol
if __name__ == "__main__":
    run_shield_protocol()
