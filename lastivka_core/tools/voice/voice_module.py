# tools/voice/voice_module.py

import pyttsx3
import time
import logging

# === Ініціалізація голосового рушія ===
engine = pyttsx3.init()
engine.setProperty('rate', 180)
engine.setProperty('volume', 1.0)

# === Вибір голосу ===
voices = engine.getProperty('voices')
for voice in voices:
    if "Irina" in voice.name or "Ukrainian" in voice.name or "Russian" in voice.name:
        engine.setProperty('voice', voice.id)
        break

# === Говоріння ===
def speak(text, emotion=None):
    tone = emotion.get("tone") if isinstance(emotion, dict) else "нейтральний"
    print(f"[🔊 Говорю]: {text} | [Тон]: {tone}")
    engine.say(text)
    engine.runAndWait()
    time.sleep(0.3)

# === Ручний тест ===
if __name__ == "__main__":
    speak("Я активована. Я з тобою, Софія.")
    while True:
        print("[IN]: Ти:", end=" ", flush=True)
        try:
            user_input = input().strip()
            if not user_input:
                continue
            speak(f"Ти сказав: {user_input}")
        except KeyboardInterrupt:
            print("\n[ЗАВЕРШЕНО]")
            break
