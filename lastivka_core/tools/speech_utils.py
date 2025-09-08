import json
import os
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from datetime import datetime

# 📁 Базовий каталог і шлях до логів помилок вимови
BASE_DIR = Path(__file__).resolve().parent.parent
PRON_ERROR_LOG = BASE_DIR / "logs" / "pronunciation_errors.json"

# 🌐 Мова озвучення
LANG = "uk"

# 🎵 Імпорт pygame для відтворення звуку
try:
    import pygame
    _PYGAME_IMPORTED = True
except Exception:
    _PYGAME_IMPORTED = False

def _ensure_mixer() -> bool:
    if not _PYGAME_IMPORTED:
        return False
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        return True
    except Exception:
        return False

# 📢 gTTS
try:
    from gtts import gTTS
    _GTTS_IMPORTED = True
except Exception:
    _GTTS_IMPORTED = False

def tts_available() -> bool:
    return _GTTS_IMPORTED and _ensure_mixer()

def _play_mp3(path: str) -> None:
    if not _ensure_mixer():
        return
    try:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
    except Exception:
        pass
    pygame.mixer.music.load(path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)

# === ІМПОРТ СТИЛЮ ТА ЕМОЦІЙ ===
from tools.emotion_engine import get_emotion
from main import style_manager as sm

def speak(text: str, **kwargs):
    """
    Озвучити текст з урахуванням стилю і емоції.
    Працює через gTTS + pygame (або лише друк, якщо недоступно).
    """

    if not text:
        return

    # 🔁 Автоадаптація стилю до емоції
    sm.auto_adjust_style_from_emotion()

    # 🧠 Отримання стилю
    styled_text, tone, speed, pause = sm.react_by_style(text)
    emotion_data = get_emotion()
    intensity = emotion_data.get("intensity", "medium")

    print(f"[TTS | {tone} | {speed} wpm | {intensity}] → {styled_text}")

    if not tts_available():
        print("⚠️ gTTS або pygame недоступні. Озвучення не відбулось.")
        return

    tmp_path = None
    try:
        with NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tmp_path = fp.name

        tts = gTTS(text=styled_text, lang=LANG)
        tts.save(tmp_path)
        _play_mp3(tmp_path)
        time.sleep(pause)

    except Exception as e:
        print(f"❌ speak() error: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

def show_pronunciation_errors(limit: int = 10):
    if not PRON_ERROR_LOG.exists():
        print("⚠️ Файл журналу помилок вимови не знайдено.")
        return

    try:
        with open(PRON_ERROR_LOG, "r", encoding="utf-8") as f:
            errors = json.load(f)
    except json.JSONDecodeError:
        print("❌ Помилка при зчитуванні JSON. Файл пошкоджено?")
        return

    if not errors:
        print("ℹ️ Немає жодного запису про помилки вимови.")
        return

    print(f"\n📊 Показую останні {min(len(errors), limit)} помилок вимови:\n")
    for err in errors[-limit:]:
        ts = err.get("timestamp", "???")
        incorrect = err.get("incorrect", "??")
        correct = err.get("correct", "??")
        source = err.get("source_phrase", "")
        time_str = datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M:%S") if isinstance(ts, str) and "T" in ts else ts
        print(f"🕒 {time_str}")
        print(f"❌ Неправильно: {incorrect}")
        print(f"✅ Правильно: {correct}")
        if source:
            print(f"🔹 Джерело: {source}")
        print("-" * 40)
