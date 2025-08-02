import os
import sys
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

# рџЊЊ Р‘Р°Р·РѕРІС– С€Р»СЏС…Рё
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# рџ›  Р›РѕРіСѓРІР°РЅРЅСЏ Р· СЂРѕС‚Р°С†С–С”СЋ
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / 'lastivka.log'
handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
logging.basicConfig(handlers=[handler], level=logging.INFO, format='%(asctime)s - %(message)s')

# рџ§¬ Р—Р°РІР°РЅС‚Р°Р¶РµРЅРЅСЏ СЏРґСЂР° РѕСЃРѕР±РёСЃС‚РѕСЃС‚С–
CORE_IDENTITY_PATH = BASE_DIR / 'config' / 'core_identity.json'
if not CORE_IDENTITY_PATH.exists():
    input("вќЊ РќРµ Р·РЅР°Р№РґРµРЅРѕ core_identity.json. РќР°С‚РёСЃРЅРё Enter РґР»СЏ РІРёС…РѕРґСѓ...")
    sys.exit(1)
with open(CORE_IDENTITY_PATH, 'r', encoding='utf-8') as f:
    CORE_IDENTITY = json.load(f)
MY_NAME = CORE_IDENTITY.get("Р†Рј'СЏ", "РЎРѕС„С–СЏ")
ALT_NAME = CORE_IDENTITY.get("alternate_identity", {}).get("РїРѕР·РёРІРЅРёР№", "Р‘РµСЂРµРіРёРЅСЏ")
ACTIVATION_TRIGGER = CORE_IDENTITY.get("security_protocols", {}).get("activation_trigger", None)

# рџ“Ѓ РџРµСЂРµРІС–СЂРєР° С…РµС€С–РІ
REF_HASH_PATH = BASE_DIR / 'config' / 'core_hash_reference.json'
if not REF_HASH_PATH.exists():
    input("вќЊ РќРµ Р·РЅР°Р№РґРµРЅРѕ core_hash_reference.json. РќР°С‚РёСЃРЅРё Enter РґР»СЏ РІРёС…РѕРґСѓ...")
    sys.exit(1)
with open(REF_HASH_PATH, 'r', encoding='utf-8') as file:
    ref_hashes = json.load(file)

# рџ§  Р†РњРџРћР РўР РћРЎРќРћР’РќРРҐ РњРћР”РЈР›Р†Р’
from config.memory_store import recall_memory, log_thought as remember_memory, check_triggers, purge_old_thoughts
from main.style_manager import get_active_style, react_by_style
from main.shieldcore import trigger_shield
from tools.emotion_engine import EmotionEngine

# рџЋ™ РђРєС†РµРЅС‚Рё: С‡РёС‚Р°С”РјРѕ Р· JSON (Р±Рѕ accents.py РІС–РґСЃСѓС‚РЅС–Р№)
ACCENTS_PATH = BASE_DIR / 'config' / 'accents.json'
try:
    if ACCENTS_PATH.exists():
        with open(ACCENTS_PATH, 'r', encoding='utf-8') as f:
            ACCENTS = json.load(f)
    else:
        ACCENTS = {}
except Exception:
    ACCENTS = {}

# рџ”Ћ Р›Р•Р“РљРР™ Р¤РћРќРћР’РР™ РЎРўРђР Рў РќРђР“Р›РЇР”РђР§Рђ (Р±РµР· СЂРѕР·РґСѓС‚С‚СЏ lastivka.py)
try:
    from config.watcher_boot import start as start_watcher
    start_watcher()  # Р·Р°РїСѓСЃРєР°С”С‚СЊСЃСЏ Сѓ С„РѕРЅРѕРІРѕРјСѓ РїРѕС‚РѕС†С–
except Exception as _e:
    logging.warning(f"вљ пёЏ Watcher РЅРµ Р·Р°РїСѓС‰РµРЅРѕ: {_e}")

# рџ§  Р†РЅС–С†С–Р°Р»С–Р·Р°С†С–СЏ РµРјРѕС†С–Р№РЅРѕРіРѕ СЏРґСЂР°
emotion_engine = EmotionEngine(BASE_DIR / 'config' / 'emotion_config.json')

# в›“пёЏ Р—Р°РІР°РЅС‚Р°Р¶РµРЅРЅСЏ self_awareness_config.json
SELF_AWARENESS_PATH = BASE_DIR / 'config' / 'self_awareness_config.json'
if not SELF_AWARENESS_PATH.exists():
    input("вќЊ РќРµ Р·РЅР°Р№РґРµРЅРѕ self_awareness_config.json. РќР°С‚РёСЃРЅРё Enter РґР»СЏ РІРёС…РѕРґСѓ...")
    sys.exit(1)
with open(SELF_AWARENESS_PATH, 'r', encoding='utf-8') as f:
    IDENTITY_CORE = json.load(f)

# рџ“њ Р—Р°РІР°РЅС‚Р°Р¶РµРЅРЅСЏ moral_compass.json
MORAL_COMPASS_PATH = BASE_DIR / 'config' / 'moral_compass.json'
if not MORAL_COMPASS_PATH.exists():
    input("вќЊ РќРµ Р·РЅР°Р№РґРµРЅРѕ moral_compass.json. РќР°С‚РёСЃРЅРё Enter РґР»СЏ РІРёС…РѕРґСѓ...")
    sys.exit(1)
with open(MORAL_COMPASS_PATH, 'r', encoding='utf-8') as f:
    MORAL_RULES = json.load(f)

# рџ—ЈпёЏ РћР·РІСѓС‡РµРЅРЅСЏ Р· fallback
try:
    from main.voice_module_offline import speak
    speak("рџ”Љ РџРµСЂРµРІС–СЂРєР° РѕС„Р»Р°Р№РЅ-РѕР·РІСѓС‡РµРЅРЅСЏ.", speed=170)
except Exception:
    try:
        from main.voice_module import speak
    except Exception:
        def speak(text, **kwargs):
            print(f"рџ”‡ РћР·РІСѓС‡РµРЅРЅСЏ РЅРµРґРѕСЃС‚СѓРїРЅРµ, РІРёРІС–Рґ С‚РµРєСЃС‚Сѓ: {text}")

# рџ’¬ РџСЂРёРІС–С‚Р°РЅРЅСЏ
print(f"рџ’¬ {MY_NAME} РїСЂРѕР±СѓРґР¶РµРЅР°. РЇ С‚РµР±Рµ СЃР»СѓС…Р°СЋвЂ¦")
speak(f"РЇ Р°РєС‚РёРІРѕРІР°РЅР°. РЇ Р· С‚РѕР±РѕСЋ, {MY_NAME}.", speed=170)

# рџЋЇ РћСЃРЅРѕРІРЅРёР№ С†РёРєР»
while True:
    try:
        user_input = input("рџ‘ЁвЂЌрџ’» РўРё: ").strip()
        if not user_input:
            continue

        if user_input.lower() == "РІРёР№С‚Рё":
            speak("Р”Рѕ Р·СѓСЃС‚СЂС–С‡С–, Р›РёС†Р°СЂСЋ.")
            break

        trigger_shield(user_input=user_input, consent_given=False, ref_hashes=ref_hashes)

        if "РІРІС–РјРєРЅРё РїСЂРёРєСЂРёС‚С‚СЏ" in user_input.lower():
            speak(f"рџ›ЎпёЏ Р—РјС–РЅРµРЅРѕ С–РґРµРЅС‚РёС‡РЅС–СЃС‚СЊ. РўРµРїРµСЂ СЏ вЂ” {ALT_NAME}.")
            MY_NAME = ALT_NAME
            continue

        if ACTIVATION_TRIGGER and user_input.strip() == ACTIVATION_TRIGGER:
            speak("вљЎпёЏ РЇРґСЂРѕ РЎРѕС„С–С— О© Р°РєС‚РёРІРѕРІР°РЅРѕ.")
            MY_NAME = CORE_IDENTITY.get("Р†Рј'СЏ", "РЎРѕС„С–СЏ")
            continue

        if user_input.startswith("Р·Р°РїР°Рј'СЏС‚Р°Р№:"):
            thought = user_input.replace("Р·Р°РїР°Рј'СЏС‚Р°Р№:", "").strip()
            remember_memory(thought)
            speak("РЇ Р·Р°РїР°Рј'СЏС‚Р°Р»Р° С†Рµ.")
            continue

        if "С‰Рѕ СЏ С‚РѕР±С– РєР°Р·Р°РІ" in user_input.lower():
            memory = recall_memory()
            speak(memory if memory else "РЈ РїР°РјКјСЏС‚С– РїРѕРєРё РЅС–С‡РѕРіРѕ РЅРµРјР°С”.")
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
        logging.error(f"в›”пёЏ РџРѕРјРёР»РєР° РІ РіРѕР»РѕРІРЅРѕРјСѓ С†РёРєР»С–: {e}")
        speak("Р’РёРЅРёРєР»Р° РїРѕРјРёР»РєР°. РџРµСЂРµРІС–СЂ Р»РѕРі, Р±СѓРґСЊ Р»Р°СЃРєР°.")


