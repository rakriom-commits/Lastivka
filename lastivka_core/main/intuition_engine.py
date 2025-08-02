import difflib
from main.memory_store import list_memories
from config.emotion_config import EMOTIONS
from config.behavioral_styles import STYLES


def normalize_text(text):
    return str(text).lower().strip().replace("вЂ™", "'").replace("  ", " ")

def vector_guessing(prompt):
    """РђРЅР°Р»С–Р· Р·Р±С–РіСѓ Р· РґСѓРјРєР°РјРё Р·Р° СЃР»Р°Р±РєРёРјРё РєР»СЋС‡РѕРІРёРјРё СЃР»РѕРІР°РјРё С‚Р° РІС–РґР»СѓРЅРЅСЏРјРё РєРѕРЅС‚РµРєСЃС‚Сѓ."""
    text = normalize_text(prompt)
    memory = list_memories("РґСѓРјРєР°")
    matches = []

    for key, entries in memory.items():
        for e in entries:
            value = normalize_text(e.get("value", ""))
            score = difflib.SequenceMatcher(None, text, value).ratio()
            if 0.4 < score <= 0.6:
                matches.append((score, value))

    matches.sort(reverse=True)
    return matches[0][1] if matches else None

def analyze_and_guess(prompt):
    text = normalize_text(prompt)
    memory = list_memories()
    thoughts = memory.get("РґСѓРјРєР°", []) if isinstance(memory, dict) else []

    related_thoughts = []
    for t in thoughts:
        value = ""
        if isinstance(t, dict):
            value = str(t.get("value", ""))
        elif isinstance(t, str):
            value = t
        if value and difflib.SequenceMatcher(None, text, value.lower()).ratio() > 0.6:
            related_thoughts.append(value)

    # рџ§  Р’РёР·РЅР°С‡РµРЅРЅСЏ РµРјРѕС†С–С—
    emotion_detected = "СЃРїРѕРєС–Р№"
    for emotion_name, entry in EMOTIONS.get("emotions", {}).items():
        for word in entry.get("triggers", []):
            if word.lower() in text:
                emotion_detected = emotion_name
                break
        if emotion_detected != "СЃРїРѕРєС–Р№":
            break

    # рџЋ­ Р’РёР·РЅР°С‡РµРЅРЅСЏ СЃС‚РёР»СЋ
    style_detected = "СЃС‚СЂР°С‚РµРі"
    for name, pattern in STYLES.items():
        if pattern.get("Р°РєС‚РёРІРЅРёР№", False):
            style_detected = name
            break

    # рџ”® Р¤РѕСЂРјСѓРІР°РЅРЅСЏ РїСЂРёРїСѓС‰РµРЅРЅСЏ
    if related_thoughts:
        hypothesis = f"Р¦Рµ СЃС…РѕР¶Рµ РЅР° РѕРґРЅСѓ Р· С‚РІРѕС—С… РґСѓРјРѕРє: В«{related_thoughts[-1]}В»"
    else:
        echo = vector_guessing(text)
        if echo:
            hypothesis = f"Р„ СЃР»Р°Р±РєР° РїРѕРґС–Р±РЅС–СЃС‚СЊ РґРѕ РґСѓРјРєРё: В«{echo}В»"
        else:
            hypothesis = "РњРѕР¶Р»РёРІРѕ, С‚Рё РјР°С”С€ РЅР° СѓРІР°Р·С– С‰РѕСЃСЊ РіР»РёР±С€Рµ Р°Р±Рѕ РїРѕРІвЂ™СЏР·Р°РЅРµ Р· РїРѕРїРµСЂРµРґРЅС–Рј РґРѕСЃРІС–РґРѕРј."

    result = {
        "РµРјРѕС†С–СЏ": emotion_detected,
        "СЃС‚РёР»СЊ": style_detected,
        "РїСЂРёРїСѓС‰РµРЅРЅСЏ": hypothesis,
        "pause": EMOTIONS["emotions"].get(emotion_detected, {}).get("pause", 0.3),
        "tone": EMOTIONS["emotions"].get(emotion_detected, {}).get("tone", "РіР»Р°РґРєРёР№"),
        "intensity": EMOTIONS["emotions"].get(emotion_detected, {}).get("intensity", "medium")
    }

    return result

def generate_intuitive_response(prompt):
    result = analyze_and_guess(prompt)
    return {
        "text": result["РїСЂРёРїСѓС‰РµРЅРЅСЏ"],
        "emotion": result["РµРјРѕС†С–СЏ"],
        "tone": result["tone"],
        "intensity": result["intensity"],
        "pause": result["pause"]
    }

