# === balcon_speech_module.py ===
import subprocess
import time
import logging

# === Налаштування за замовчуванням ===
DEFAULT_VOICE = "RHVoice Natalia"
DEFAULT_SPEED = 180
DEFAULT_VOLUME = 100
DEFAULT_PITCH = 0

# === Функція озвучення через Balcon ===
def speak(text, emotion=None):
    if not isinstance(text, str) or not text.strip():
        return

    voice = DEFAULT_VOICE
    speed = DEFAULT_SPEED
    volume = DEFAULT_VOLUME
    pitch = DEFAULT_PITCH

    # === Якщо передано емоцію — адаптуємо голос ===
    if isinstance(emotion, dict):
        tone = emotion.get("tone", "нейтральний")
        intensity = emotion.get("intensity", "medium")

        if tone == "радісний":
            pitch += 10
            speed += 20
        elif tone == "сумний":
            pitch -= 10
            speed -= 20
        elif tone == "злий":
            volume += 10
            pitch += 5
        elif tone == "спокійний":
            speed -= 10
        elif tone == "натхненний":
            pitch += 15
            speed += 15
        elif tone == "сором’язливий":
            pitch -= 5
            speed -= 10
        elif tone == "впевнений":
            pitch += 5
            volume += 5

    # === Формуємо команду ===
    command = [
        "C:\\ProgramData\\chocolatey\\lib\\balcon\\tools\\balcon.exe",
        "-n", voice,
        "-t", text,
        "-s", str(speed),
        "-v", str(volume),
        "-p", str(pitch)
    ]

    try:
        subprocess.run(command, check=True)
    except Exception as e:
        logging.error(f"[balcon_speech_module] ❌ Помилка озвучення: {e}")

    time.sleep(0.1)  # затримка між фразами, якщо підряд