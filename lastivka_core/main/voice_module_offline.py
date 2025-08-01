import pyttsx3
import time

# 🎙️ Ініціалізація озвучення
engine = pyttsx3.init()

# 🗣️ Встановлення українського голосу (якщо доступний)
def set_ukrainian_voice():
    for voice in engine.getProperty("voices"):
        if "ukrainian" in voice.name.lower() or "uk-ua" in voice.id.lower():
            engine.setProperty("voice", voice.id)
            return True
    return False

ua_available = set_ukrainian_voice()

# 🧹 Стиль → на майбутнє: мапа стилів (optional)
STYLE_MAP = {
    "енергійний": {"rate": 210},
    "співчутливий": {"rate": 140},
    "ласкавий": {"rate": 160},
    "жорсткий": {"rate": 190},
    "обережний": {"rate": 150},
    "твердо": {"rate": 180},
    "врівноважено": {"rate": 160},
    "натхненно": {"rate": 200},
    "емоційно": {"rate": 170},
    "несміливо": {"rate": 130},
    "вдячно": {"rate": 165}
}

# 🔨 Озвучення з підтримкою емоцій
def speak(text, emotion=None, tone=None, intensity=None, speed=170, pause=0.0, style=None):
    try:
        # ⏸️ Пауза перед
        if pause and pause > 0:
            time.sleep(pause)

        # 🛠️ Обрати стиль як пріоритет
        if style and style in STYLE_MAP:
            engine.setProperty("rate", STYLE_MAP[style]["rate"])
        else:
            engine.setProperty("rate", speed)

        # 🔈 Озвучити текст
        engine.say(text)
        engine.runAndWait()

        # ⏸️ Пауза після
        if pause and pause > 0.2:
            time.sleep(pause * 0.8)

    except Exception as e:
        print(f"⚠️ Помилка озвучення: {e}")
        print("📝 Текст, який не вдалося озвучити:", text)