# === LASTIVKA Ω: Збір відгуків щодо вимови та природності мовлення ===

import json
from datetime import datetime
from pathlib import Path

# === Шляхи до логів і памʼяті ===
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
CONFIG_DIR = BASE_DIR / "config"

PRON_ERROR_LOG = LOG_DIR / "pronunciation_errors.json"
MEMORY_STORE = LOG_DIR / "memory_store.json"

# === 1. Логування помилок вимови ===
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

# === 2. Оцінка природності мови та запис у памʼять ===
def evaluate_speech(naturalness: int) -> str:
    feedback = {
        3: "Чудово! Вимова звучить природно, чітко і зрозуміло.",
        2: "Досить добре, але є незначні проблеми з інтонацією або паузами.",
        1: "Мова звучить неприродно. Варто попрацювати над темпом, наголосами та емоцією."
    }

    result = feedback.get(naturalness, "Не вдалося оцінити мовлення.")

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

# === Приклад запуску модуля напряму ===
if __name__ == "__main__":
    log_pron_error("лєґенда", "легенда", "А ти знаєш, що таке лєґенда?")
    print(evaluate_speech(2))
