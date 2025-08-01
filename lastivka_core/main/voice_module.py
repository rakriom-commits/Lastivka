
import json
import pygame
import tempfile
from pathlib import Path
from gtts import gTTS
from datetime import datetime

# === Шляхи ===
ACCENTS_PATH = Path(__file__).resolve().parent.parent / "config" / "accents.json"
AUDIO_LOG_DIR = Path(__file__).resolve().parent.parent / "temp" / "audio_log"
AUDIO_LOG_DIR.mkdir(parents=True, exist_ok=True)

ACCENTS = {}
if ACCENTS_PATH.exists():
    try:
        with open(ACCENTS_PATH, "r", encoding="utf-8") as f:
            ACCENTS = json.load(f)
    except Exception as e:
        print(f"⚠️ Помилка читання accents.json: {e}")

def fix_accents(text: str) -> str:
    for wrong, correct in ACCENTS.items():
        text = text.replace(wrong, correct)
        text = text.replace(wrong.capitalize(), correct.capitalize())
    return text

def fallback_text(emotion: str, tone: str, text: str) -> str:
    prefix = ""
    if emotion in ["смуток", "страх"]:
        prefix = "*тихо:* "
    elif emotion in ["любов", "вдячність", "сором"]:
        prefix = "*ніжно:* "
    elif emotion in ["злість"]:
        prefix = "*різко:* "
    elif emotion in ["гордість", "натхнення"]:
        prefix = "*впевнено:* "
    return f"{prefix}{text}"

def speak(text: str, emotion: str = "спокій", tone: str = "гладкий", intensity: str = "medium", speed: int = 170):
    if not isinstance(text, str) or not text.strip():
        print("⚠️ Текст для озвучення має бути непорожнім рядком.")
        return

    fixed_text = fix_accents(text)
    styled_text = fallback_text(emotion, tone, fixed_text)
    print(f"🗣️ {styled_text}")

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
        print(f"❌ Помилка озвучення: {e}")
    finally:
        try:
            pygame.mixer.quit()
        except:
            pass
