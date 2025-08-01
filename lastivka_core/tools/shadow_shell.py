import time

LOCKED = True
UNLOCK_PHRASE = "Подох — котяра"


def trigger_shell():
    global LOCKED
    print("\n🔒 Активація захисного протоколу: ShadowShell")
    time.sleep(1)
    print("...\n⚠️ Система заблокована. Введи фразу розблокування:")

    while LOCKED:
        attempt = input("🔐 Фраза: ").strip()
        if attempt == UNLOCK_PHRASE:
            LOCKED = False
            print("\n🟢 Розблоковано. Продовжую роботу.\n")
        else:
            print("❌ Неправильно. Спробуй ще.")


def is_locked():
    return LOCKED
