# === EMOTION ENGINE О© ===

from config.emotion_config import EMOTIONS
from main.lastivka_skill import get_emotional_profile

def detect_emotion(text: str):
    """
    Р’РёР·РЅР°С‡Р°С” РµРјРѕС†С–СЋ РЅР° РѕСЃРЅРѕРІС– С‚СЂРёРіРµСЂС–РІ Сѓ С‚РµРєСЃС‚С– РєРѕСЂРёСЃС‚СѓРІР°С‡Р°.
    РџРѕРІРµСЂС‚Р°С”: (РµРјРѕС†С–СЏ, С€РІРёРґРєС–СЃС‚СЊ, РіРѕР»РѕСЃРѕРІР°_СЂРµР°РєС†С–СЏ, РµРјРѕС†С–Р№РЅРёР№_РїСЂРѕС„С–Р»СЊ)
    """
    emotions_data = EMOTIONS.get("emotions", [])
    speed_map = EMOTIONS.get("speed", {})
    text_lower = text.lower() if isinstance(text, str) else ""

    for entry in emotions_data:
        emotion = entry.get("Р•РјРѕС†С–СЏ", "").lower()
        for trigger in entry.get("РЎР»РѕРІР°", []):
            if trigger.lower() in text_lower:
                speed = speed_map.get(emotion, speed_map.get("default", 170))
                voice_response = entry.get("Р РµР°РєС†С–СЏ", "")
                profile = get_emotional_profile(emotion)
                return emotion, speed, voice_response, profile

    # РЇРєС‰Рѕ РЅРµ Р·РЅР°Р№РґРµРЅРѕ вЂ” РЅРµР№С‚СЂР°Р»СЊРЅР° РµРјРѕС†С–СЏ
    return (
        "РЅРµР№С‚СЂР°Р»СЊРЅР°",
        speed_map.get("default", 170),
        "СЃРїРѕРєС–Р№РЅРёР№, Р±Р°Р·РѕРІРёР№ С‚РѕРЅ",
        get_emotional_profile("РЅРµР№С‚СЂР°Р»СЊРЅР°")
    )

if __name__ == "__main__":
    test = "РјРµРЅС– СЃС‚СЂР°С€РЅРѕ Р·Р°Р»РёС€Р°С‚РёСЃСЊ РЅР°РѕРґРёРЅС†С–"
    emotion, speed, voice, profile = detect_emotion(test)
    print(f"рџ§  Р•РјРѕС†С–СЏ: {emotion}")
    print(f"рџЋљ РЁРІРёРґРєС–СЃС‚СЊ: {speed}")
    print(f"рџ—Ј Р РµР°РєС†С–СЏ: {voice}")
    print("рџЋ­ РџРѕРІРµРґС–РЅРєР°:")
    for key, value in profile.items():
        print(f"  {key.capitalize()}: {value}")

