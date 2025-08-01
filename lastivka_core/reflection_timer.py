import threading
import time
from core_reflection import generate_reflection, save_reflection

# ⏱️ Інтервал (у секундах) — можна змінити
REFLECTION_INTERVAL = 300  # 5 хвилин

def start_reflection_timer():
    def run():
        print(f"[ReflectionTimer] Старт кожні {REFLECTION_INTERVAL} секунд...")
        while True:
            try:
                reflection = generate_reflection("Системна тиша. Самоаналіз.")
                save_reflection(reflection)
            except Exception as e:
                print(f"[ReflectionTimer] Помилка під час рефлексії: {e}")
            time.sleep(REFLECTION_INTERVAL)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()