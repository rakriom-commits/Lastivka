# === LASTIVKA О©: РјРѕРґСѓР»СЊ РѕС†С–РЅРєРё РјРѕРІР»РµРЅРЅСЏ С‚Р° РІРёРјРѕРІРё ===

import json
from datetime import datetime
from pathlib import Path

# в–‘в–‘в–‘ РЁР›РЇРҐР в–‘в–‘в–‘
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
CONFIG_DIR = BASE_DIR / "config"

PRON_ERROR_LOG = LOG_DIR / "pronunciation_errors.json"
MEMORY_STORE = CONFIG_DIR / "memory_store.json"

# в–‘в–‘в–‘ 1. Р—Р°РїРёСЃ РїРѕРјРёР»РєРё РІРёРјРѕРІРё в–‘в–‘в–‘
def log_pron_error(incorrect: str, correct: str, source_phrase: str = ""):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "incorrect": incorrect,
        "correct": correct,
        "source_phrase": source_phrase
    }

    if PRON_ERROR_LOG.exists():
        with open(PRON_ERROR_LOG, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

    data.append(entry)

    with open(PRON_ERROR_LOG, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# в–‘в–‘в–‘ 2. РћС†С–РЅРєР° РјРѕРІР»РµРЅРЅСЏ в–‘в–‘в–‘
def evaluate_speech(naturalness: int) -> str:
    feedback = {
        3: "Р§СѓРґРѕРІРѕ! РњРѕРІР»РµРЅРЅСЏ Р·РІСѓС‡Р°Р»Рѕ РїСЂРёСЂРѕРґРЅРѕ С– РїСЂРёС”РјРЅРѕ.",
        2: "Р—РІСѓС‡Р°Р»Рѕ РЅРµРїРѕРіР°РЅРѕ, Р°Р»Рµ С‚СЂРѕС…Рё РЅРµРїСЂРёСЂРѕРґРЅРѕ.",
        1: "РџРѕРіР°РЅРёР№ РЅР°РіРѕР»РѕСЃ Р°Р±Рѕ С–РЅС‚РѕРЅР°С†С–СЏ. РџРѕС‚СЂРµР±СѓС” РїРѕРєСЂР°С‰РµРЅРЅСЏ."
    }

    result = feedback.get(naturalness, "РћС†С–РЅРєР° РЅРµ СЂРѕР·РїС–Р·РЅР°РЅР°")

    log = {
        "timestamp": datetime.now().isoformat(),
        "type": "speech_evaluation",
        "score": naturalness,
        "feedback": result
    }

    if MEMORY_STORE.exists():
        with open(MEMORY_STORE, "r", encoding="utf-8") as f:
            memory = json.load(f)
    else:
        memory = []

    memory.append(log)

    with open(MEMORY_STORE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

    return result

# в–‘в–‘в–‘ РџСЂРёРєР»Р°Рґ РІРёРєРѕСЂРёСЃС‚Р°РЅРЅСЏ в–‘в–‘в–‘
if __name__ == "__main__":
    log_pron_error("Р·РђСЂР°Р·", "Р·Р°СЂР°Р·", "РўРё Р·РђСЂР°Р· РєСѓРґРё?")
    print(evaluate_speech(2))

