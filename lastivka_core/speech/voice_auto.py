# === Voice AutoSwitch Module ===
import socket
import importlib

def internet_available(host="8.8.8.8", port=53, timeout=2):
    """Перевіряє наявність інтернету через DNS-запит."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception:
        return False

# Визначаємо, який модуль використовувати
if internet_available():
    voice_module = importlib.import_module("main.voice_module")  # онлайн (gTTS)
else:
    voice_module = importlib.import_module("main.voice_module_offline")  # офлайн (pyttsx3)

# Експортуємо функцію speak з обраного модуля
speak = voice_module.speak
