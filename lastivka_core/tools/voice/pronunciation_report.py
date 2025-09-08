# pronunciation_report.py
import json
from pathlib import Path
from operator import itemgetter

ERRORS_PATH = Path(__file__).resolve().parent.parent / "config" / "pronunciation_errors.json"

# Завантажити дані

def load_errors():
    if not ERRORS_PATH.exists():
        return []
    with open(ERRORS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("log", [])

# Вивести звіт

def generate_report(limit=10):
    errors = load_errors()
    if not errors:
        print("[Report] Журнал порожній.")
        return

    print("=== ТОП помилок вимови ===")
    sorted_errors = sorted(errors, key=itemgetter("count"), reverse=True)

    for i, entry in enumerate(sorted_errors[:limit], start=1):
        print(f"{i}. {entry['incorrect']} → {entry['correct']}  | Випадків: {entry['count']}")
        if entry.get("examples"):
            print(f"   ↳ Приклад: {entry['examples'][0]['source_phrase']}")
        print()

# === Приклад запуску ===
if __name__ == "__main__":
    generate_report(limit=5)