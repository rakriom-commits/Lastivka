import json
import os
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from datetime import datetime

# ===📁 Шляхи ===
BASE_DIR = Path(__file__).resolve().parent.parent
PRON_ERROR_LOG = BASE_DIR / "logs" / "pronunciation_errors.json"

# ===🔊 Озвучення ===
LANG = "uk"

# pygame може бути відсутнім — ініціалізуємо мікшер м’яко
try:
    import pygame
    _PYGAME_IMPORTED = True
except Exception:
    _PYGAME_IMPORTED = False

def _ensure_mixer() -> bool:
    """Ледача ініціалізація/перевірка pygame.mixer."""
    if not _PYGAME_IMPORTED:
        return False
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        return True
    except Exception:
        return False

# gTTS також не гарантується
try:
    from gtts import gTTS
    _GTTS_IMPORTED = True
except Exception:
    _GTTS_IMPORTED = False


def tts_available() -> bool:
    """Чи доступне повноцінне TTS (gTTS + pygame.mixer)?"""
    return _GTTS_IMPORTED and _ensure_mixer()


def _play_mp3(path: str) -> None:
    """Відтворення MP3 через pygame.mixer з очікуванням кінця."""
    if not _ensure_mixer():
        return
    # Якщо щось уже грає — зупиняємо
    try:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
    except Exception:
        pass

    pygame.mixer.music.load(path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)


def speak(text: str, **kwargs):
    """
    Озвучує текст через gTTS + pygame (якщо доступні).
    Додаткові параметри (**kwargs) ігноруються (сумісність із викликами типу speed=..., emotion=...).
    Завжди дублює текст у консоль у форматі [🔊]: ...
    """
    if not text:
        return

    print(f"[🔊]: {text}")

    # Якщо немає залежностей — просто консольний вивід
    if not (_GTTS_IMPORTED and _ensure_mixer()):
        if not _GTTS_IMPORTED:
            print("⚠️ gTTS недоступний: озвучую лише в консоль.")
        if not _ensure_mixer():
            print("⚠️ pygame.mixer недоступний: озвучую лише в консоль.")
        return

    tmp_path = None
    try:
        # 1) Тимчасовий файл (Windows-friendly)
        with NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tmp_path = fp.name

        # 2) Генерація озвучення
        tts = gTTS(text=text, lang=LANG)
        tts.save(tmp_path)

        # 3) Відтворення
        _play_mp3(tmp_path)

    except Exception as e:
        print(f"❌ speak() error: {e}")
    finally:
        # 4) Прибирання тимчасового файлу
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def show_pronunciation_errors(limit: int = 10):
    """
    Виводить останні помилки вимови з лог-файлу.
    :param limit: кількість записів (default=10)
    """
    if not PRON_ERROR_LOG.exists():
        print("❌ Файл логів помилок вимови не знайдено.")
        return

    try:
        with open(PRON_ERROR_LOG, "r", encoding="utf-8") as f:
            errors = json.load(f)
    except json.JSONDecodeError:
        print("⚠️ Неможливо прочитати JSON. Файл пошкоджено?")
        return

    if not errors:
        print("🟢 Жодних записаних помилок вимови.")
        return

    print(f"\n📘 Останні {min(len(errors), limit)} помилки вимови:\n")
    for err in errors[-limit:]:
        ts = err.get("timestamp", "—")
        incorrect = err.get("incorrect", "??")
        correct = err.get("correct", "??")
        source = err.get("source_phrase", "")
        time_str = datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M:%S") if isinstance(ts, str) and "T" in ts else ts
        print(f"🕒 {time_str}")
        print(f"🔻 Некоректно: {incorrect}")
        print(f"✅ Правильно: {correct}")
        if source:
            print(f"💬 Фраза: {source}")
        print("-" * 40)
