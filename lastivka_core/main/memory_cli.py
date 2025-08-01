import sys
import os
from pathlib import Path

# 🔁 Динамічне додавання шляху до lastivka_core
BASE_DIR = Path(__file__).resolve().parent.parent / "lastivka_core"
sys.path.append(str(BASE_DIR))

try:
    from memory_manager import remember, recall, forget, list_memories, recall_from_question
except ImportError:
    print("\033[91m❌ Не вдалося імпортувати memory_manager. Перевір шлях до lastivka_core.\033[0m")
    sys.exit(1)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_menu():
    print("\033[96m\n🧠 LASTIVKA MEMORY CLI\033[0m")
    print("1. ➕ Запамʼятати")
    print("2. 🔍 Пригадати за ключем")
    print("3. ❓ Пригадати з питання")
    print("4. 📋 Уся памʼять")
    print("5. 🧹 Забути")
    print("6. 📦 Показати архів")
    print("0. 🚪 Вийти")

def print_memory_block(memory):
    for key, value in memory.items():
        print(f"\n🔑 {key}:")
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    print(f"  🕓 {item.get('timestamp')} | 🎼 {item.get('tone')} | 💬 {item.get('value')}")
                else:
                    print(f"  - {item}")
        else:
            if isinstance(value, dict):
                print(f"  🕓 {value.get('timestamp')} | 🎼 {value.get('tone')} | 💬 {value.get('value')}")
            else:
                print(f"  - {value}")

def main():
    while True:
        clear_screen()
        show_menu()
        choice = input("\n🔸 \033[93mОбери дію:\033[0m ").strip()

        if choice == "1":
            key = input("🗝️ \033[94mКлюч:\033[0m ").strip()
            value = input("💭 \033[94mЗначення:\033[0m ").strip()
            tone = input("🎼 \033[94mТональність (напр. нейтральна, емоційна):\033[0m ").strip()
            remember(key, value, tone=tone)
            input("\033[92m✅ Збережено. Натисни Enter для продовження...\033[0m")

        elif choice == "2":
            key = input("🗝️ \033[94mКлюч для пошуку:\033[0m ").strip()
            result = recall(key)
            print("\033[92m📥 Результат:\033[0m")
            if result:
                print_memory_block({key: result})
            else:
                print("Нічого не знайдено.")
            input("\nНатисни Enter для продовження...")

        elif choice == "3":
            question = input("❓ \033[94mПитання:\033[0m ").strip()
            result = recall_from_question(question)
            print("\033[92m📥 Відповідь:\033[0m\n", result or "Нічого не знайдено.")
            input("\nНатисни Enter для продовження...")

        elif choice == "4":
            memory = list_memories()
            if not memory:
                print("\n\033[91m🕳 Памʼять порожня.\033[0m")
            else:
                print("\n\033[92m🧾 Уся памʼять:\033[0m")
                print_memory_block(memory)
            input("\nНатисни Enter для продовження...")

        elif choice == "5":
            key = input("🗑️ \033[94mКлюч для забування:\033[0m ").strip()
            forget(key)
            input("\033[92m✅ Забуто, якщо було. Натисни Enter для продовження...\033[0m")

        elif choice == "6":
            archive = list_memories(archive=True)
            if not archive:
                print("\n\033[91m🕳 Архів порожній.\033[0m")
            else:
                print("\n\033[95m📦 Архів памʼяті:\033[0m")
                print_memory_block(archive)
            input("\nНатисни Enter для продовження...")

        elif choice == "0":
            print("\n\033[96m👋 До зустрічі, Лицарю.\033[0m")
            break

        else:
            input("\033[91m⚠️ Невірний вибір. Спробуй ще раз. Натисни Enter...\033[0m")

if __name__ == "__main__":
    main()
