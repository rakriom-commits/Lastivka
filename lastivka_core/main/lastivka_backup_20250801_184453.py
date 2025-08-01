import os
import sys
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

# 🌌 Базові шляхи
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# 🛠 Логування з ротацією
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / 'lastivka.log'
handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
logging.basicConfig(handlers=[handler], level=logging.INFO, format='%(asctime)s - %(message)s')

# 🧬 Завантаження ядра особистості
CORE_IDENTITY_PATH = BASE_DIR / 'config' / 'core_identity.json'
if not CORE_IDENTITY_PATH.exists():
    input("❌ Не знайдено core_identity.json. Натисни Enter для виходу...")
    sys.exit(1)
with open(CORE_IDENTITY_PATH, 'r', encoding='utf-8') as f:
    CORE_IDENTITY = json.load(f)
MY_NAME = CORE_IDENTITY.get("Ім'я", "Софія")
ALT_NAME = CORE_IDENTITY.get("alternate_identity", {}).get("позивний", "Берегиня")
ACTIVATION_TRIGGER = CORE_IDENTITY.get("security_protocols", {}).get("activation_trigger", None)

# 📁 Перевірка хешів
REF_HASH_PATH = BASE_DIR / 'config' / 'core_hash_reference.json'
if not REF_HASH_PATH.exists():
    input("❌ Не знайдено core_hash_reference.json. Натисни Enter для виходу...")
    sys.exit(1)
with open(REF_HASH_PATH, 'r', encoding='utf-8') as file:
    ref_hashes = json.load(file)

# 🧠 ІМПОРТИ ОСНОВНИХ МОДУЛІВ
from config.memory_store import recall_memory, log_thought as remember_memory, check_triggers, purge_old_thoughts
from main.style_manager import get_active_style, react_by_style
from main.shieldcore import trigger_shield
from tools.emotion_engine import EmotionEngine

# 🎙 Акценти: читаємо з JSON (бо accents.py відсутній)
ACCENTS_PATH = BASE_DIR / 'config' / 'accents.json'
try:
    if ACCENTS_PATH.exists():
        with open(ACCENTS_PATH, 'r', encoding='utf-8') as f:
            ACCENTS = json.load(f)
    else:
        ACCENTS = {}
except Exception:
    ACCENTS = {}

# 🔎 ЛЕГКИЙ ФОНОВИЙ СТАРТ НАГЛЯДАЧА (без роздуття lastivka.py)
try:
    from config.watcher_boot import start as start_watcher
    start_watcher()  # запускається у фоновому потоці
except Exception as _e:
    logging.warning(f"⚠️ Watcher не запущено: {_e}")

# 🧠 Ініціалізація емоційного ядра
emotion_engine = EmotionEngine(BASE_DIR / 'config' / 'emotion_config.json')

# ⛓️ Завантаження self_awareness_config.json
SELF_AWARENESS_PATH = BASE_DIR / 'config' / 'self_awareness_config.json'
if not SELF_AWARENESS_PATH.exists():
    input("❌ Не знайдено self_awareness_config.json. Натисни Enter для виходу...")
    sys.exit(1)
with open(SELF_AWARENESS_PATH, 'r', encoding='utf-8') as f:
    IDENTITY_CORE = json.load(f)

# 📜 Завантаження moral_compass.json
MORAL_COMPASS_PATH = BASE_DIR / 'config' / 'moral_compass.json'
if not MORAL_COMPASS_PATH.exists():
    input("❌ Не знайдено moral_compass.json. Натисни Enter для виходу...")
    sys.exit(1)
with open(MORAL_COMPASS_PATH, 'r', encoding='utf-8') as f:
    MORAL_RULES = json.load(f)

# 🗣️ Озвучення з fallback
try:
    from main.voice_module_offline import speak
    speak("🔊 Перевірка офлайн-озвучення.", speed=170)
except Exception:
    try:
        from main.voice_module import speak
    except Exception:
        def speak(text, **kwargs):
            print(f"🔇 Озвучення недоступне, вивід тексту: {text}")

# 💬 Привітання
print(f"💬 {MY_NAME} пробуджена. Я тебе слухаю…")
speak(f"Я активована. Я з тобою, {MY_NAME}.", speed=170)

# 🎯 Основний цикл
while True:
    try:
        user_input = input("👨‍💻 Ти: ").strip()
        if not user_input:
            continue

        if user_input.lower() == "вийти":
            speak("До зустрічі, Лицарю.")
            break

        trigger_shield(user_input=user_input, consent_given=False, ref_hashes=ref_hashes)

        if "ввімкни прикриття" in user_input.lower():
            speak(f"🛡️ Змінено ідентичність. Тепер я — {ALT_NAME}.")
            MY_NAME = ALT_NAME
            continue

        if ACTIVATION_TRIGGER and user_input.strip() == ACTIVATION_TRIGGER:
            speak("⚡️ Ядро Софії Ω активовано.")
            MY_NAME = CORE_IDENTITY.get("Ім'я", "Софія")
            continue

        if user_input.startswith("запам'ятай:"):
            thought = user_input.replace("запам'ятай:", "").strip()
            remember_memory(thought)
            speak("Я запам'ятала це.")
            continue

        if "що я тобі казав" in user_input.lower():
            memory = recall_memory()
            speak(memory if memory else "У памʼяті поки нічого немає.")
            continue

        trigger_response = check_triggers(user_input)
        if trigger_response:
            speak(trigger_response)

        emotion = emotion_engine.detect_emotion(user_input)
        style = get_active_style()
        response = react_by_style(user_input, emotion, style, accents=ACCENTS if ACCENTS else None)
        speak(response, emotion=emotion)

        logging.info(f"[USER]: {user_input}")
        logging.info(f"[RESPONSE]: {response} | [Emotion]: {emotion}")

    except KeyboardInterrupt:
        break
    except Exception as e:
        logging.error(f"⛔️ Помилка в головному циклі: {e}")
        speak("Виникла помилка. Перевір лог, будь ласка.")
