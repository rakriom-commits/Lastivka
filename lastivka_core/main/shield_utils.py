import hashlib
import json
import os
from pathlib import Path
from datetime import datetime

# рџ“Ѓ Р‘Р°Р·РѕРІР° РґРёСЂРµРєС‚РѕСЂС–СЏ СЏРґСЂР°
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_PATH = BASE_DIR / "logs" / "shield_events.log"
BACKUP_PATH = BASE_DIR / "backups"

# рџ›ЎпёЏ РџРµСЂРµРІС–СЂРєР° С†С–Р»С–СЃРЅРѕСЃС‚С–

def hash_file(file_path):
    h = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()
    except FileNotFoundError:
        return None

def verify_core_integrity(ref_hashes):
    tampered_files = []
    for name, ref_hash in ref_hashes.items():
        file_path = BASE_DIR / name
        current_hash = hash_file(file_path)
        if current_hash != ref_hash:
            tampered_files.append(name)
    return tampered_files if tampered_files else None

# рџ“ќ Р›РѕРіСѓРІР°РЅРЅСЏ РїРѕРґС–Р№ Р±РµР·РїРµРєРё

def log_shield_event(message):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as log:
            log.write(f"{datetime.now().isoformat()} вЂ” {message}\n")
    except Exception as e:
        print(f"вљ пёЏ РџРѕРјРёР»РєР° Р»РѕРіСѓРІР°РЅРЅСЏ РїРѕРґС–С—: {e}")

# рџ’ѕ Р РµР·РµСЂРІРЅРµ РєРѕРїС–СЋРІР°РЅРЅСЏ СЏРґСЂР°

def backup_core():
    try:
        BACKUP_PATH.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = BACKUP_PATH / f"backup_{timestamp}"
        backup_dir.mkdir()

        critical_files = [
            "lastivka.py",
            "config/memory_store.json",
            "config/self_awareness_config.json",
            "config/core_hash_reference.json",
            "config/moral_compass.json",
            "main/intuition_engine.py",
            "main/memory_store.py",
            "main/style_manager.py"
        ]

        for rel_path in critical_files:
            src = BASE_DIR / rel_path
            dst = backup_dir / Path(rel_path).name
            if src.exists():
                with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
                    fdst.write(fsrc.read())

        log_shield_event(f"РЎС‚РІРѕСЂРµРЅРѕ СЂРµР·РµСЂРІРЅСѓ РєРѕРїС–СЋ: {backup_dir.name}")
    except Exception as e:
        log_shield_event(f"РџРѕРјРёР»РєР° СЂРµР·РµСЂРІРЅРѕРіРѕ РєРѕРїС–СЋРІР°РЅРЅСЏ: {e}")

