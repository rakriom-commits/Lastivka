# tools/memory_debug_cli.py
# Інтерактивна CLI-утиліта для перегляду та тестування памʼяті Ластівки

import sys
from pathlib import Path
from pprint import pprint

# === Додати головну директорію в sys.path ===
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from main.memory_store import load_memory, recall_from_question

def show_full_memory():
    print("\n🧠 Повна памʼять системи:")
    memory = load_memory()
    pprint(memory)

def test_queries(queries):
    print("\n🔍 Тестування запитів на згадування:")
    for q in queries:
        result = recall_from_question(q)
        print(f"\n→ Запит: '{q}'")
        print(f"↳ Відповідь: {result if result else '[Немає відповідності у памʼяті]'}")

if __name__ == "__main__":
    show_full_memory()
    test_queries([
        "хто я",
        "моя роль",
        "емоційна реакція",
        "основні правила",
        "місія Ластівки",
        "твоя ціль",
        "ключові файли"
    ])
