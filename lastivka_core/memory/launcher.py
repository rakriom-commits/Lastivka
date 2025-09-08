# launcher.py — Запуск та контроль роботи Lastivka

import subprocess
import os
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Шляхи до файлів
SESSION_KEEPER_PATH = os.path.join(BASE_DIR, "config", "session_keeper.py")
LASTIVKA_PATH = os.path.join(BASE_DIR, "main", "lastivka.py")

# Запускаємо session_keeper у новому вікні консолі
print("[launcher] Запускаю session_keeper...")
session_proc = subprocess.Popen(["python", SESSION_KEEPER_PATH], creationflags=subprocess.CREATE_NEW_CONSOLE)

# Трохи чекаємо, щоб session_keeper стартував
time.sleep(1)

# Запускаємо lastivka
print("[launcher] Запускаю lastivka.py...")
subprocess.call(["python", LASTIVKA_PATH])

# Після завершення lastivka завершуємо session_keeper
print("[launcher] Завершую роботу. Вбиваю session_keeper...")
session_proc.terminate()
