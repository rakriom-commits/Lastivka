# generate_core_hashes.py — генерація еталонних хешів ядра для ShieldCore

import json
import sys
from pathlib import Path

# ░░░ Автоматичне додавання базового шляху
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from main import shieldcore

# ░░░ Шлях до файлу еталону
CONFIG_PATH = BASE_DIR / "config"
HASH_PATH = CONFIG_PATH / "core_hash_reference.json"

def generate_hash_reference():
    CONFIG_PATH.mkdir(parents=True, exist_ok=True)
    hashes = {Path(f).name: shieldcore.calculate_hash(f) for f in shieldcore.MONITORED_FILES}
    with open(HASH_PATH, "w", encoding="utf-8") as f:
        json.dump(hashes, f, indent=2, ensure_ascii=False)
    print("✅ core_hash_reference.json збережено.")
    for name, h in hashes.items():
        print(f"  • {name}: {h}")

# ░░░ Запуск
if __name__ == "__main__":
    generate_hash_reference()
