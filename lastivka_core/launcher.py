# launcher.py — запуск основних модулів Lastivka

import subprocess
import os
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Шляхи до скриптів
SESSION_KEEPER_PATH = os.path.join(BASE_DIR, "config", "session_keeper.py")
LASTIVKA_PATH = os.path.join(BASE_DIR, "main", "lastivka.py")

# Запуск session_keeper у фоновому режимі
print("[launcher] Запускаю session_keeper...")
session_proc = subprocess.Popen(["python", SESSION_KEEPER_PATH], creationflags=subprocess.CREATE_NEW_CONSOLE)

# Невелика пауза для стабільності
time.sleep(1)

# Запуск lastivka
print("[launcher] Запускаю lastivka.py...")
subprocess.call(["python", LASTIVKA_PATH])

# Якщо lastivka закрився — завершуємо фоновий процес
print("[launcher] Завершення. Зупиняю session_keeper...")
session_proc.terminate()
