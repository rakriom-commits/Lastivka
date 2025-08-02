import time
import threading
import json
import random
from pathlib import Path
from tools.watchdog import verify_core_integrity, backup_core, log_shield_event
from tools.config_loader import load_json_config
from tools.shadow_shell import trigger_shell, is_locked

# рџ”ђ РљР»СЋС‡РѕРІС– С„Р°Р№Р»Рё РґР»СЏ РјРѕРЅС–С‚РѕСЂРёРЅРіСѓ
CORE_FILES = [
    Path("config/core_identity.json"),
    Path("config/moral_compass.json"),
    Path("config/emotion_config.json"),
    Path("config/self_awareness_config.json"),
    Path("main/lastivka.py"),
    Path("main/shieldcore.py"),
]

CHECK_INTERVAL = 30  # СЃРµРєСѓРЅРґ

# рџ“Ґ Р—Р°РІР°РЅС‚Р°Р¶РµРЅРЅСЏ СЂРµС„РµСЂРµРЅСЃРЅРёС… С…РµС€С–РІ
def load_reference_hashes():
    try:
        with open("config/core_hash_reference.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log_shield_event(f"РџРѕРјРёР»РєР° Р·Р°РІР°РЅС‚Р°Р¶РµРЅРЅСЏ С…РµС€С–РІ: {e}")
        return {}

# рџ›ЎпёЏ РћСЃРЅРѕРІРЅРёР№ РєР»Р°СЃ Р·Р°С…РёСЃС‚Сѓ
class ShadowShell:
    def __init__(self):
        self.ref_hashes = load_reference_hashes()
        self.running = False

    def monitor_core(self):
        while self.running:
            tampered = verify_core_integrity(self.ref_hashes, CORE_FILES)
            if tampered:
                log_shield_event(f"ShadowShell: Р’РёСЏРІР»РµРЅРѕ РїРѕСЂСѓС€РµРЅРЅСЏ Сѓ {tampered}")
                backup_core()
                self.activate_shield()
            time.sleep(CHECK_INTERVAL)

    def activate_shield(self):
        log_shield_event("ShadowShell: РђРєС‚РёРІРѕРІР°РЅРѕ Р·Р°С…РёСЃРЅРёР№ СЂРµР¶РёРј (Р—Р°РІС–СЃР°)")
        force_lockdown()

    def start(self):
        self.running = True
        thread = threading.Thread(target=self.monitor_core, daemon=True)
        thread.start()
        print("рџ›ЎпёЏ ShadowShell Protocol Р°РєС‚РёРІРѕРІР°РЅРѕ.")

    def stop(self):
        self.running = False
        print("рџ›‘ ShadowShell Protocol Р·СѓРїРёРЅРµРЅРѕ.")

# рџЋ­ Р—Р°РІР°РЅС‚Р°Р¶РµРЅРЅСЏ СЂРµР°РєС†С–Р№
reaction_templates = load_json_config("config/reaction_templates.json")

def respond_from_template(key: str):
    """РџРѕРІРµСЂС‚Р°С” РІРёРїР°РґРєРѕРІСѓ СЂРµР°РєС†С–СЋ Р·Р° РєР»СЋС‡РµРј С€Р°Р±Р»РѕРЅСѓ."""
    return random.choice(reaction_templates.get(key, ["[!] РќРµРјР°С” СЂРµР°РєС†С–С—."]))

def run_shield_protocol():
    """Р—Р°РїСѓСЃРєР°С” РїРµСЂРµРІС–СЂРєСѓ Р±РµР·РїРµРєРё Р· СЂРµР°РєС†С–СЏРјРё."""
    if is_locked():
        print(respond_from_template("intrusion_detected"))
        trigger_shell()
    else:
        print(respond_from_template("unlock_granted"))

def force_lockdown():
    """РџСЂРёРјСѓСЃРѕРІРѕ Р±Р»РѕРєСѓС” СЃРёСЃС‚РµРјСѓ Р· С€Р°Р±Р»РѕРЅРѕРј СЂРµР°РєС†С–С—."""
    print(respond_from_template("locked_mode_active"))
    trigger_shell()

# рџ§Є РўРµСЃС‚
if __name__ == "__main__":
    run_shield_protocol()

