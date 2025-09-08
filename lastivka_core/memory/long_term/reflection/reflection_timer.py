import threading
import time
from core_reflection import generate_reflection, save_reflection

# Інтервал між рефлексіями (в секундах)
REFLECTION_INTERVAL = 300  # 5 хвилин

def start_reflection_timer():
    def run():
        print(f"[ReflectionTimer] Стартуємо рефлексії кожні {REFLECTION_INTERVAL} секунд...")
        while True:
            try:
                reflection = generate_reflection("Рефлексія Ластівки. Час подумати.")
                save_reflection(reflection)
            except Exception as e:
                print(f"[ReflectionTimer] Помилка при генерації або збереженні рефлексії: {e}")
            time.sleep(REFLECTION_INTERVAL)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
