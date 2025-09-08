import json
from pathlib import Path
from gtts import gTTS
import pygame
import time
from main.lastivka_skill import get_emotional_profile

# === Ініціалізація голосового движка через pygame ===
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
        print(f"[ПОМИЛКА] Озвучення не вдалося: {e}")

def load_json(path: str | Path):
    path = Path(path)
    if not path.exists():
        print(f"[ПОМИЛКА] Файл не знайдено: {path}")
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ПОМИЛКА] Помилка при читанні JSON: {e}")
        return {}

# === Завантаження особистості, емоцій та памʼяті ===
identity = load_json("core_identity.json")
emotions = load_json("emotion_config.json").get("emotions", [])
memory = load_json("memory_store.json")

# === Вступне звернення до користувача ===
intro = "Вітаю. Я — Ластівка. Я тут, щоб підтримати тебе. Готова діяти. Дякую, що запустив мене."
print(intro)
speak(intro)

# === Демонстрація вибраної емоції та реакції ===
emotion = "спокій"
profile = get_emotional_profile(emotion)

reaction_text = (
    f"Обрана емоція: {emotion}. "
    f"Опис: {profile.get('опис', '')}. "
    f"Реакція: {profile.get('реакція', '')}. "
    f"Тон: {profile.get('тон', '')}"
)

print(reaction_text)
speak(reaction_text)
