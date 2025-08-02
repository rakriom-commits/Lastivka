
import json
import pygame
import tempfile
from pathlib import Path
from gtts import gTTS
from datetime import datetime

# === РЁР»СЏС…Рё ===
ACCENTS_PATH = Path(__file__).resolve().parent.parent / "config" / "accents.json"
AUDIO_LOG_DIR = Path(__file__).resolve().parent.parent / "temp" / "audio_log"
AUDIO_LOG_DIR.mkdir(parents=True, exist_ok=True)

ACCENTS = {}
if ACCENTS_PATH.exists():
    try:
        with open(ACCENTS_PATH, "r", encoding="utf-8") as f:
            ACCENTS = json.load(f)
    except Exception as e:
        print(f"вљ пёЏ РџРѕРјРёР»РєР° С‡РёС‚Р°РЅРЅСЏ accents.json: {e}")

def fix_accents(text: str) -> str:
    for wrong, correct in ACCENTS.items():
        text = text.replace(wrong, correct)
        text = text.replace(wrong.capitalize(), correct.capitalize())
    return text

def fallback_text(emotion: str, tone: str, text: str) -> str:
    prefix = ""
    if emotion in ["СЃРјСѓС‚РѕРє", "СЃС‚СЂР°С…"]:
        prefix = "*С‚РёС…Рѕ:* "
    elif emotion in ["Р»СЋР±РѕРІ", "РІРґСЏС‡РЅС–СЃС‚СЊ", "СЃРѕСЂРѕРј"]:
        prefix = "*РЅС–Р¶РЅРѕ:* "
    elif emotion in ["Р·Р»С–СЃС‚СЊ"]:
        prefix = "*СЂС–Р·РєРѕ:* "
    elif emotion in ["РіРѕСЂРґС–СЃС‚СЊ", "РЅР°С‚С…РЅРµРЅРЅСЏ"]:
        prefix = "*РІРїРµРІРЅРµРЅРѕ:* "
    return f"{prefix}{text}"

def speak(text: str, emotion: str = "СЃРїРѕРєС–Р№", tone: str = "РіР»Р°РґРєРёР№", intensity: str = "medium", speed: int = 170):
    if not isinstance(text, str) or not text.strip():
        print("вљ пёЏ РўРµРєСЃС‚ РґР»СЏ РѕР·РІСѓС‡РµРЅРЅСЏ РјР°С” Р±СѓС‚Рё РЅРµРїРѕСЂРѕР¶РЅС–Рј СЂСЏРґРєРѕРј.")
        return

    fixed_text = fix_accents(text)
    styled_text = fallback_text(emotion, tone, fixed_text)
    print(f"рџ—ЈпёЏ {styled_text}")

    try:
        tts = gTTS(text=styled_text, lang='uk')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_path = AUDIO_LOG_DIR / f"line_{timestamp}.mp3"
        tts.save(temp_path)

        pygame.mixer.init()
        pygame.mixer.music.load(str(temp_path))
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except Exception as e:
        print(f"вќЊ РџРѕРјРёР»РєР° РѕР·РІСѓС‡РµРЅРЅСЏ: {e}")
    finally:
        try:
            pygame.mixer.quit()
        except:
            pass

