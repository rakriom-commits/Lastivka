import sys
from pathlib import Path
from pprint import pprint

# ░░░ Шлях до проєкту ░░░
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from main.memory_store import load_memory, recall_from_question

def show_full_memory():
    print("\n🔎 Повна пам’ять:")
    memory = load_memory()
    pprint(memory)

def test_queries(queries):
    print("\n🧪 Тест запитів:")
    for q in queries:
        result = recall_from_question(q)
        print(f"\n🔍 Запит: '{q}'")
        print(f"📌 Відповідь: {result if result else '— нічого не знайдено'}")

if __name__ == "__main__":
    show_full_memory()
    test_queries(["каву", "кава", "чорну каву", "цукор", "сон", "думка", "біль"])
