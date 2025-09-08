# session_keeper.py — Підтримка сесії для проєкту Lastivka

import time
import json
from datetime import datetime

SESSION_FILE = "session_status.json"
PING_INTERVAL = 900  # 15 хвилин

# Функція оновлює файл статусу сесії з поточним часом і станом
def update_session_status():
    status = {
        "last_active": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_thought": "Мережеве пінгування для живої підтримки",
        "step": "Періодичне оновлення"
    }
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
    print(f"[session_keeper] Статус сесії оновлено: {status['last_active']}")

# Цикл підтримки активності сесії
def keep_session_alive():
    print("[session_keeper] Запускаю механізм підтримки сесії...")
    try:
        while True:
            update_session_status()
            time.sleep(PING_INTERVAL)
    except KeyboardInterrupt:
        print("[session_keeper] Роботу перервано вручну.")

if __name__ == "__main__":
    keep_session_alive()
