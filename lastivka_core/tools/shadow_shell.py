# lastivka_core/tools/shadow_shell.py

import time

# === Стан блокування ===
LOCKED = True
UNLOCK_PHRASE = "Подох — котяра"  # ← контрольна фраза для розблокування

def trigger_shell():
    global LOCKED
    print("\n🔐 Активація захисної оболонки ShadowShell")
    time.sleep(1)
    print("...\n⚠️ Увага! Система заблокована. Для розблокування введи контрольну фразу:")

    while LOCKED:
        attempt = input("🔑 Введи фразу: ").strip()
        if attempt == UNLOCK_PHRASE:
            LOCKED = False
            print("\n✅ Доступ дозволено. Режим захисту деактивовано.\n")
        else:
            print("❌ Невірна фраза. Спробуй ще раз.")

def is_locked():
    return LOCKED
