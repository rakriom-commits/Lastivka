import json
from pathlib import Path
from gtts import gTTS
import pygame
import time
from main.lastivka_skill import get_emotional_profile

# === Р†РЅС–С†С–Р°Р»С–Р·Р°С†С–СЏ pygame ===
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
        print(f"вќЊ РџРѕРјРёР»РєР° РѕР·РІСѓС‡РµРЅРЅСЏ: {e}")

def load_json(path: str | Path):
    path = Path(path)
    if not path.exists():
        print(f"вљ пёЏ Р¤Р°Р№Р» РЅРµ Р·РЅР°Р№РґРµРЅРѕ: {path}")
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"вќЊ РџРѕРјРёР»РєР° С‡РёС‚Р°РЅРЅСЏ JSON: {e}")
        return {}

# === Р—Р°РІР°РЅС‚Р°Р¶РµРЅРЅСЏ РґР°РЅРёС… ===
identity = load_json("core_identity.json")
emotions = load_json("emotion_config.json").get("emotions", [])
memory = load_json("memory_store.json")

# === Р’СЃС‚СѓРїРЅРµ РїРѕРІС–РґРѕРјР»РµРЅРЅСЏ ===
intro = "РџСЂРёРІС–С‚. РЇ РЎРѕС„С–СЏ. РЇ С‚СѓС‚, С‰РѕР± Р±СѓС‚Рё РїРѕСЂСѓС‡. Р—Р°РІР¶РґРё. РџРѕРєРё С‚Рё РґРёС…Р°С”С€ вЂ” СЏ Р· С‚РѕР±РѕСЋ."
print(intro)
speak(intro)

# === Р”РµРјРѕРЅСЃС‚СЂР°С†С–СЏ РµРјРѕС†С–Р№РЅРѕС— СЂРµР°РєС†С–С— ===
emotion = "СЃРјСѓС‚РѕРє"
profile = get_emotional_profile(emotion)

reaction_text = (
    f"РЎРѕС„С–СЏ РІС–РґС‡СѓРІР°С” {emotion}. "
    f"РўРѕРЅ: {profile.get('С‚РѕРЅ', '')}. "
    f"РџРѕРІРѕРґРёС‚СЊСЃСЏ: {profile.get('СЂРµР¶РёРј', '')}. "
    f"Р”С–СЏ: {profile.get('РґС–СЏ', '')}"
)

print(reaction_text)
speak(reaction_text)

