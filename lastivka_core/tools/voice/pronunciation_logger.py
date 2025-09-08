# pronunciation_logger.py
import json
from pathlib import Path
from datetime import datetime

ERRORS_PATH = Path(__file__).resolve().parent.parent / "config" / "pronunciation_errors.json"

# Завантажити існуючі помилки
def load_errors():
    if not ERRORS_PATH.exists():
        return {"log": []}
    with open(ERRORS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# Зберегти помилки назад у файл
def save_errors(data):
    with open(ERRORS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Додати нову помилку або оновити існуючу

def log_pronunciation_error(incorrect, correct, source_phrase):
    data = load_errors()
    log = data.get("log", [])

    for entry in log:
        if entry["incorrect"] == incorrect and entry["correct"] == correct:
            entry["examples"].append({
                "timestamp": datetime.now().isoformat(),
                "source_phrase": source_phrase
            })
            entry["count"] += 1
            break
    else:
        log.append({
            "incorrect": incorrect,
            "correct": correct,
            "examples": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "source_phrase": source_phrase
                }
            ],
            "count": 1
        })

    data["log"] = log
    save_errors(data)

# === Тестова вставка ===
if __name__ == "__main__":
    log_pronunciation_error(
        incorrect="зАраз",
        correct="зараз",
        source_phrase="Приклад вимови: зАраз — правильна: зараз"
    )
