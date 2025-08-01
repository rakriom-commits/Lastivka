import json
from pathlib import Path
from gtts import gTTS
import pygame
import time
from main.lastivka_skill import get_emotional_profile

# === Ініціалізація pygame ===
pygame.mixer.init()

def speak(text):
    try:
        tts = gTTS(text=text, lang='uk')
        temp_file = "sofia_voice.mp3"
        tts.save(temp_file)
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
    except Exception as e:
        print(f"❌ Помилка озвучення: {e}")

def load_json(path: str | Path):
    path = Path(path)
    if not path.exists():
        print(f"⚠️ Файл не знайдено: {path}")
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Помилка читання JSON: {e}")
        return {}

# === Завантаження даних ===
identity = load_json("core_identity.json")
emotions = load_json("emotion_config.json").get("emotions", [])
memory = load_json("memory_store.json")

# === Вступне повідомлення ===
intro = "Привіт. Я Софія. Я тут, щоб бути поруч. Завжди. Поки ти дихаєш — я з тобою."
print(intro)
speak(intro)

# === Демонстрація емоційної реакції ===
emotion = "смуток"
profile = get_emotional_profile(emotion)

reaction_text = (
    f"Софія відчуває {emotion}. "
    f"Тон: {profile.get('тон', '')}. "
    f"Поводиться: {profile.get('режим', '')}. "
    f"Дія: {profile.get('дія', '')}"
)

print(reaction_text)
speak(reaction_text)
