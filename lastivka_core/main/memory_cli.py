import sys
import os
from pathlib import Path

# рџ”Ѓ Р”РёРЅР°РјС–С‡РЅРµ РґРѕРґР°РІР°РЅРЅСЏ С€Р»СЏС…Сѓ РґРѕ lastivka_core
BASE_DIR = Path(__file__).resolve().parent.parent / "lastivka_core"
sys.path.append(str(BASE_DIR))

try:
    from memory_manager import remember, recall, forget, list_memories, recall_from_question
except ImportError:
    print("\033[91mвќЊ РќРµ РІРґР°Р»РѕСЃСЏ С–РјРїРѕСЂС‚СѓРІР°С‚Рё memory_manager. РџРµСЂРµРІС–СЂ С€Р»СЏС… РґРѕ lastivka_core.\033[0m")
    sys.exit(1)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_menu():
    print("\033[96m\nрџ§  LASTIVKA MEMORY CLI\033[0m")
    print("1. вћ• Р—Р°РїР°РјКјСЏС‚Р°С‚Рё")
    print("2. рџ”Ќ РџСЂРёРіР°РґР°С‚Рё Р·Р° РєР»СЋС‡РµРј")
    print("3. вќ“ РџСЂРёРіР°РґР°С‚Рё Р· РїРёС‚Р°РЅРЅСЏ")
    print("4. рџ“‹ РЈСЃСЏ РїР°РјКјСЏС‚СЊ")
    print("5. рџ§№ Р—Р°Р±СѓС‚Рё")
    print("6. рџ“¦ РџРѕРєР°Р·Р°С‚Рё Р°СЂС…С–РІ")
    print("0. рџљЄ Р’РёР№С‚Рё")

def print_memory_block(memory):
    for key, value in memory.items():
        print(f"\nрџ”‘ {key}:")
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    print(f"  рџ•“ {item.get('timestamp')} | рџЋј {item.get('tone')} | рџ’¬ {item.get('value')}")
                else:
                    print(f"  - {item}")
        else:
            if isinstance(value, dict):
                print(f"  рџ•“ {value.get('timestamp')} | рџЋј {value.get('tone')} | рџ’¬ {value.get('value')}")
            else:
                print(f"  - {value}")

def main():
    while True:
        clear_screen()
        show_menu()
        choice = input("\nрџ”ё \033[93mРћР±РµСЂРё РґС–СЋ:\033[0m ").strip()

        if choice == "1":
            key = input("рџ—ќпёЏ \033[94mРљР»СЋС‡:\033[0m ").strip()
            value = input("рџ’­ \033[94mР—РЅР°С‡РµРЅРЅСЏ:\033[0m ").strip()
            tone = input("рџЋј \033[94mРўРѕРЅР°Р»СЊРЅС–СЃС‚СЊ (РЅР°РїСЂ. РЅРµР№С‚СЂР°Р»СЊРЅР°, РµРјРѕС†С–Р№РЅР°):\033[0m ").strip()
            remember(key, value, tone=tone)
            input("\033[92mвњ… Р—Р±РµСЂРµР¶РµРЅРѕ. РќР°С‚РёСЃРЅРё Enter РґР»СЏ РїСЂРѕРґРѕРІР¶РµРЅРЅСЏ...\033[0m")

        elif choice == "2":
            key = input("рџ—ќпёЏ \033[94mРљР»СЋС‡ РґР»СЏ РїРѕС€СѓРєСѓ:\033[0m ").strip()
            result = recall(key)
            print("\033[92mрџ“Ґ Р РµР·СѓР»СЊС‚Р°С‚:\033[0m")
            if result:
                print_memory_block({key: result})
            else:
                print("РќС–С‡РѕРіРѕ РЅРµ Р·РЅР°Р№РґРµРЅРѕ.")
            input("\nРќР°С‚РёСЃРЅРё Enter РґР»СЏ РїСЂРѕРґРѕРІР¶РµРЅРЅСЏ...")

        elif choice == "3":
            question = input("вќ“ \033[94mРџРёС‚Р°РЅРЅСЏ:\033[0m ").strip()
            result = recall_from_question(question)
            print("\033[92mрџ“Ґ Р’С–РґРїРѕРІС–РґСЊ:\033[0m\n", result or "РќС–С‡РѕРіРѕ РЅРµ Р·РЅР°Р№РґРµРЅРѕ.")
            input("\nРќР°С‚РёСЃРЅРё Enter РґР»СЏ РїСЂРѕРґРѕРІР¶РµРЅРЅСЏ...")

        elif choice == "4":
            memory = list_memories()
            if not memory:
                print("\n\033[91mрџ•і РџР°РјКјСЏС‚СЊ РїРѕСЂРѕР¶РЅСЏ.\033[0m")
            else:
                print("\n\033[92mрџ§ѕ РЈСЃСЏ РїР°РјКјСЏС‚СЊ:\033[0m")
                print_memory_block(memory)
            input("\nРќР°С‚РёСЃРЅРё Enter РґР»СЏ РїСЂРѕРґРѕРІР¶РµРЅРЅСЏ...")

        elif choice == "5":
            key = input("рџ—‘пёЏ \033[94mРљР»СЋС‡ РґР»СЏ Р·Р°Р±СѓРІР°РЅРЅСЏ:\033[0m ").strip()
            forget(key)
            input("\033[92mвњ… Р—Р°Р±СѓС‚Рѕ, СЏРєС‰Рѕ Р±СѓР»Рѕ. РќР°С‚РёСЃРЅРё Enter РґР»СЏ РїСЂРѕРґРѕРІР¶РµРЅРЅСЏ...\033[0m")

        elif choice == "6":
            archive = list_memories(archive=True)
            if not archive:
                print("\n\033[91mрџ•і РђСЂС…С–РІ РїРѕСЂРѕР¶РЅС–Р№.\033[0m")
            else:
                print("\n\033[95mрџ“¦ РђСЂС…С–РІ РїР°РјКјСЏС‚С–:\033[0m")
                print_memory_block(archive)
            input("\nРќР°С‚РёСЃРЅРё Enter РґР»СЏ РїСЂРѕРґРѕРІР¶РµРЅРЅСЏ...")

        elif choice == "0":
            print("\n\033[96mрџ‘‹ Р”Рѕ Р·СѓСЃС‚СЂС–С‡С–, Р›РёС†Р°СЂСЋ.\033[0m")
            break

        else:
            input("\033[91mвљ пёЏ РќРµРІС–СЂРЅРёР№ РІРёР±С–СЂ. РЎРїСЂРѕР±СѓР№ С‰Рµ СЂР°Р·. РќР°С‚РёСЃРЅРё Enter...\033[0m")

if __name__ == "__main__":
    main()

