# auto_stress_updater.py
import json
from collections import Counter
from pathlib import Path

# Шляхи до конфігурацій
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
ERROR_LOG = CONFIG_DIR / "pronunciation_errors.json"
STRESS_DICT = CONFIG_DIR / "stress_dict.json"
UPDATE_LOG = CONFIG_DIR / "stress_update.log"

# Мінімальна кількість повторень, щоб вважати слово достовірним
THRESHOLD = 2

# Завантаження журналу вимовних помилок
def load_errors():
    with open(ERROR_LOG, "r", encoding="utf-8") as f:
        return json.load(f).get("log", [])

# Завантаження stress_dict.json
def load_stress_dict():
    try:
        with open(STRESS_DICT, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Збереження stress_dict.json
def save_stress_dict(data):
    with open(STRESS_DICT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Логування доданого слова

def log_update(word, stressed):
    with open(UPDATE_LOG, "a", encoding="utf-8") as f:
        f.write(f"[StressUpdater] Додано: {word} → {stressed}\n")

# Основна функція оновлення словника наголосів

def autoupdate_stress_dict():
    errors = load_errors()
    counter = Counter()
    latest_corrected = {}

    for entry in errors:
        incorrect = entry["incorrect"].lower()
        correct = entry["correct"]
        counter[incorrect] += 1
        latest_corrected[incorrect] = correct

    stress_dict = load_stress_dict()
    updated = False

    for word, count in counter.items():
        if count >= THRESHOLD and word not in stress_dict:
            stressed = latest_corrected[word]
            stress_dict[word] = stressed
            log_update(word, stressed)
            print(f"[StressUpdater] Додано до stress_dict: {word} → {stressed} (випадків: {count})")
            updated = True

    if updated:
        save_stress_dict(stress_dict)
        print("[StressUpdater] Оновлення завершене. Файл збережено.")
    else:
        print("[StressUpdater] Нових слів для додавання не знайдено.")

# === Запуск модуля ===
if __name__ == "__main__":
    autoupdate_stress_dict()