# pronunciation_cleaner.py
import json
from pathlib import Path
from datetime import datetime

ERRORS_PATH = Path(__file__).resolve().parent.parent / "config" / "pronunciation_errors.json"

# Завантажити помилки

def load_errors():
    if not ERRORS_PATH.exists():
        return {"log": []}
    with open(ERRORS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# Зберегти назад

def save_errors(data):
    with open(ERRORS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Очистити: обʼєднати дублі, прибрати пусті, сортувати

def clean_pronunciation_log():
    data = load_errors()
    log = data.get("log", [])

    cleaned = {}

    for entry in log:
        key = (entry["incorrect"], entry["correct"])
        if key not in cleaned:
            cleaned[key] = {
                "incorrect": entry["incorrect"],
                "correct": entry["correct"],
                "examples": [],
                "count": 0
            }

        for ex in entry.get("examples", []):
            if ex not in cleaned[key]["examples"]:
                cleaned[key]["examples"].append(ex)
                cleaned[key]["count"] += 1

    # Сортуємо по кількості
    sorted_log = sorted(cleaned.values(), key=lambda x: x["count"], reverse=True)
    data["log"] = sorted_log
    save_errors(data)

    print(f"[Cleaner] Очищено. Записів залишилось: {len(sorted_log)}")

# === Приклад запуску ===
if __name__ == "__main__":
    clean_pronunciation_log()