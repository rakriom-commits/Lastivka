# === LASTIVKA Ω: модуль оцінки мовлення та вимови ===

import json
from datetime import datetime
from pathlib import Path

# ░░░ ШЛЯХИ ░░░
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
CONFIG_DIR = BASE_DIR / "config"

PRON_ERROR_LOG = LOG_DIR / "pronunciation_errors.json"
MEMORY_STORE = CONFIG_DIR / "memory_store.json"

# ░░░ 1. Запис помилки вимови ░░░
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

# ░░░ 2. Оцінка мовлення ░░░
def evaluate_speech(naturalness: int) -> str:
    feedback = {
        3: "Чудово! Мовлення звучало природно і приємно.",
        2: "Звучало непогано, але трохи неприродно.",
        1: "Поганий наголос або інтонація. Потребує покращення."
    }

    result = feedback.get(naturalness, "Оцінка не розпізнана")

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

# ░░░ Приклад використання ░░░
if __name__ == "__main__":
    log_pron_error("зАраз", "зараз", "Ти зАраз куди?")
    print(evaluate_speech(2))
