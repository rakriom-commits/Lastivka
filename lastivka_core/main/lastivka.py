import sys
import json
import time
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime

# ===== Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
sys.path.append(str(BASE_DIR))

# ===== Logging
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "lastivka.log"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")],
    force=True
)

# ===== Load configs (DRY)
def load_config(path: Path, required: bool = True):
    if not path.exists():
        if required:
            input(f"❌ Не знайдено {path.name}. Натисни Enter для виходу...")
            sys.exit(1)
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}

CORE_IDENTITY = load_config(CONFIG_DIR / "core_identity.json")
SELF_AWARENESS = load_config(CONFIG_DIR / "self_awareness_config.json")
MORAL_COMPASS = load_config(CONFIG_DIR / "moral_compass.json")
ACCENTS = load_config(CONFIG_DIR / "accents.json", required=False)
REF_HASHES = load_config(CONFIG_DIR / "core_hash_reference.json")

# ===== State
class BotConfig:
    def __init__(self):
        self.mute = False
        self.tts_delay = 0.40
        self.last_tts_ts = 0.0
        self.name = CORE_IDENTITY.get("Ім'я", "Софія")
        self.alt_name = CORE_IDENTITY.get("alternate_identity", {}).get("позивний", "Берегиня")
        self.activation = CORE_IDENTITY.get("security_protocols", {}).get("activation_trigger", None)

CFG = BotConfig()

# ===== Imports
from config.memory_store import recall_memory, log_thought as remember_memory, check_triggers
from main.style_manager import get_active_style, react_by_style
from main.shieldcore import trigger_shell
from tools.emotion_engine import EmotionEngine
from main.handlers import COMMANDS, handle_intents  # <-- handlers.py

# ===== Watcher
try:
    from config.watcher_boot import start as start_watcher
    start_watcher()
except Exception as e:
    logging.warning(f"⚠️ Watcher не запущено: {e}")

# ===== TTS
def resolve_speak():
    backends = [
        ("tools.speech_utils", "speak"),
        ("main.voice_module_offline", "speak"),
        ("main.voice_module", "speak"),
    ]
    for module, func in backends:
        try:
            mod = __import__(module, fromlist=[func])
            print(f"🔊 TTS backend: {module}")
            return getattr(mod, func)
        except Exception:
            continue
    def _fallback(text, **kwargs):
        print(f"🔇 Озвучення недоступне, вивід тексту: {text}")
    print("🔊 TTS backend: console-fallback")
    return _fallback

_speak = resolve_speak()

def say(text: str, **kwargs):
    if text is None:
        text = ""
    print(f"🗨️ {text}")
    if CFG.mute:
        return
    now = time.time()
    delta = now - CFG.last_tts_ts
    if delta < CFG.tts_delay:
        time.sleep(CFG.tts_delay - delta)
    try:
        _speak(text, **kwargs)
    except TypeError:
        _speak(text)  # backend doesn't accept kwargs like speed/emotion
    except Exception as e:
        print(f"🔇 TTS error: {e}")
    CFG.last_tts_ts = time.time()

# ===== Emotion engine
emotion_engine = EmotionEngine(CONFIG_DIR / "emotion_config.json")

# ===== Shield adapter (simple)
def trigger_shield(user_input: str, consent_given: bool = False, ref_hashes: dict | None = None):
    try:
        return trigger_shell(user_input=user_input, consent_given=consent_given, ref_hashes=ref_hashes or REF_HASHES)
    except Exception:
        return None

# ===== Main
def main_loop():
    print(f"💬 {CFG.name} пробуджена. Я тебе слухаю…")
    say(f"Я активована. Я з тобою, {CFG.name}.")
    while True:
        try:
            user_input = input("👨‍💻 Ти: ").strip()
            if not user_input:
                continue
            low = user_input.lower()

            # Команди з handlers.py
            if low in COMMANDS:
                COMMANDS[low](CFG, say, LOG_FILE, CONFIG_DIR)
                continue

            # Інтенти високого рівня (handlers.py)
            if handle_intents(user_input, CFG, say, CORE_IDENTITY, recall_memory, remember_memory):
                continue

            # Shield & triggers
            trigger_shield(user_input=user_input, consent_given=False, ref_hashes=REF_HASHES)
            trigger_response = check_triggers(user_input)
            if trigger_response:
                say(trigger_response)

            # Emotion/style → response
            try:
                emotion = emotion_engine.detect_emotion(user_input)
            except Exception as e:
                logging.error(f"[emotion.detect] {e}")
                emotion = {"emotion": None, "tone": "нейтральний", "intensity": "medium"}
            try:
                style = get_active_style() or {}
            except Exception as e:
                logging.error(f"[get_active_style] {e}")
                style = {}

            try:
                response = react_by_style(user_input, emotion, style, accents=ACCENTS or None)
            except TypeError:
                response = react_by_style(user_input, emotion, style)
            except Exception as e:
                logging.error(f"[react_by_style] {e}")
                response = None

            if not response or not isinstance(response, str):
                response = "Я з тобою. Продовжуй, будь ласка."

            say(response, emotion=emotion)
            logging.info(f"[USER]: {user_input}")
            logging.info(f"[RESPONSE]: {response} | [Emotion]: {emotion}")

        except KeyboardInterrupt:
            break
        except SystemExit:
            raise
        except Exception as e:
            logging.error(f"⛔️ Помилка: {e}")
            say("Виникла помилка. Перевір лог, будь ласка.")

if __name__ == "__main__":
    main_loop()
