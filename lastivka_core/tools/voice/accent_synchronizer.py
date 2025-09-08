# accent_synchronizer.py
import json
from pathlib import Path

ERRORS_PATH = Path(__file__).resolve().parent.parent / "config" / "pronunciation_errors.json"
ACCENTS_PATH = Path(__file__).resolve().parent.parent / "config" / "accents.json"

# Завантаження помилок вимови
def load_pronunciation_errors():
    if not ERRORS_PATH.exists():
        return []
    with open(ERRORS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("log", [])

# Завантаження наявного accents.json
def load_accents():
    if not ACCENTS_PATH.exists():
        return {}
    with open(ACCENTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# Збереження у accents.json
def save_accents(accent_map):
    with open(ACCENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(accent_map, f, ensure_ascii=False, indent=2)

# Синхронізація: додати правильні вимови з журналу помилок у accents.json
def sync_accents_from_errors():
    errors = load_pronunciation_errors()
    accents = load_accents()
    added = 0

    for entry in errors:
        incorrect = entry["incorrect"].lower()
        correct = entry["correct"]
        if incorrect not in accents:
            accents[incorrect] = correct
            added += 1

    save_accents(accents)
    print(f"[Sync] Додано {added} нових записів до accents.json")

# === Приклад запуску ===
if __name__ == "__main__":
    sync_accents_from_errors()
