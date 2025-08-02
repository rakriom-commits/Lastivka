import pyttsx3
import time

# рџЋ™пёЏ Р†РЅС–С†С–Р°Р»С–Р·Р°С†С–СЏ РѕР·РІСѓС‡РµРЅРЅСЏ
engine = pyttsx3.init()

# рџ—ЈпёЏ Р’СЃС‚Р°РЅРѕРІР»РµРЅРЅСЏ СѓРєСЂР°С—РЅСЃСЊРєРѕРіРѕ РіРѕР»РѕСЃСѓ (СЏРєС‰Рѕ РґРѕСЃС‚СѓРїРЅРёР№)
def set_ukrainian_voice():
    for voice in engine.getProperty("voices"):
        if "ukrainian" in voice.name.lower() or "uk-ua" in voice.id.lower():
            engine.setProperty("voice", voice.id)
            return True
    return False

ua_available = set_ukrainian_voice()

# рџ§№ РЎС‚РёР»СЊ в†’ РЅР° РјР°Р№Р±СѓС‚РЅС”: РјР°РїР° СЃС‚РёР»С–РІ (optional)
STYLE_MAP = {
    "РµРЅРµСЂРіС–Р№РЅРёР№": {"rate": 210},
    "СЃРїС–РІС‡СѓС‚Р»РёРІРёР№": {"rate": 140},
    "Р»Р°СЃРєР°РІРёР№": {"rate": 160},
    "Р¶РѕСЂСЃС‚РєРёР№": {"rate": 190},
    "РѕР±РµСЂРµР¶РЅРёР№": {"rate": 150},
    "С‚РІРµСЂРґРѕ": {"rate": 180},
    "РІСЂС–РІРЅРѕРІР°Р¶РµРЅРѕ": {"rate": 160},
    "РЅР°С‚С…РЅРµРЅРЅРѕ": {"rate": 200},
    "РµРјРѕС†С–Р№РЅРѕ": {"rate": 170},
    "РЅРµСЃРјС–Р»РёРІРѕ": {"rate": 130},
    "РІРґСЏС‡РЅРѕ": {"rate": 165}
}

# рџ”Ё РћР·РІСѓС‡РµРЅРЅСЏ Р· РїС–РґС‚СЂРёРјРєРѕСЋ РµРјРѕС†С–Р№
def speak(text, emotion=None, tone=None, intensity=None, speed=170, pause=0.0, style=None):
    try:
        # вЏёпёЏ РџР°СѓР·Р° РїРµСЂРµРґ
        if pause and pause > 0:
            time.sleep(pause)

        # рџ› пёЏ РћР±СЂР°С‚Рё СЃС‚РёР»СЊ СЏРє РїСЂС–РѕСЂРёС‚РµС‚
        if style and style in STYLE_MAP:
            engine.setProperty("rate", STYLE_MAP[style]["rate"])
        else:
            engine.setProperty("rate", speed)

        # рџ”€ РћР·РІСѓС‡РёС‚Рё С‚РµРєСЃС‚
        engine.say(text)
        engine.runAndWait()

        # вЏёпёЏ РџР°СѓР·Р° РїС–СЃР»СЏ
        if pause and pause > 0.2:
            time.sleep(pause * 0.8)

    except Exception as e:
        print(f"вљ пёЏ РџРѕРјРёР»РєР° РѕР·РІСѓС‡РµРЅРЅСЏ: {e}")
        print("рџ“ќ РўРµРєСЃС‚, СЏРєРёР№ РЅРµ РІРґР°Р»РѕСЃСЏ РѕР·РІСѓС‡РёС‚Рё:", text)
