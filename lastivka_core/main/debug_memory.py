import sys
from pathlib import Path
from pprint import pprint

# в–‘в–‘в–‘ РЁР»СЏС… РґРѕ РїСЂРѕС”РєС‚Сѓ в–‘в–‘в–‘
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from main.memory_store import load_memory, recall_from_question

def show_full_memory():
    print("\nрџ”Ћ РџРѕРІРЅР° РїР°РјвЂ™СЏС‚СЊ:")
    memory = load_memory()
    pprint(memory)

def test_queries(queries):
    print("\nрџ§Є РўРµСЃС‚ Р·Р°РїРёС‚С–РІ:")
    for q in queries:
        result = recall_from_question(q)
        print(f"\nрџ”Ќ Р—Р°РїРёС‚: '{q}'")
        print(f"рџ“Њ Р’С–РґРїРѕРІС–РґСЊ: {result if result else 'вЂ” РЅС–С‡РѕРіРѕ РЅРµ Р·РЅР°Р№РґРµРЅРѕ'}")

if __name__ == "__main__":
    show_full_memory()
    test_queries(["РєР°РІСѓ", "РєР°РІР°", "С‡РѕСЂРЅСѓ РєР°РІСѓ", "С†СѓРєРѕСЂ", "СЃРѕРЅ", "РґСѓРјРєР°", "Р±С–Р»СЊ"])

