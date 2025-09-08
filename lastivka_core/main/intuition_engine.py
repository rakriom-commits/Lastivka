import difflib
from main.memory_store import list_memories
from tools.emotion_config_loader import EMOTIONS
from config.behavioral_styles import STYLES

def normalize_text(text):
    return str(text).lower().strip().replace("’", "'").replace("  ", " ")

def vector_guessing(prompt):
    """Пошук схожих думок із пам’яті для слабкої інтуїції."""
    text = normalize_text(prompt)
    memory = list_memories("thoughts")
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
    thoughts = memory.get("thoughts", []) if isinstance(memory, dict) else []

    related_thoughts = []
    for t in thoughts:
        value = ""
        if isinstance(t, dict):
            value = str(t.get("value", ""))
        elif isinstance(t, str):
            value = t
        if value and difflib.SequenceMatcher(None, text, value.lower()).ratio() > 0.6:
            related_thoughts.append(value)

    # Визначення емоції
    emotion_detected = "спокій"
    for emotion_name, entry in EMOTIONS.get("emotions", {}).items():
        for word in entry.get("triggers", []):
            if word.lower() in text:
                emotion_detected = emotion_name
                break
        if emotion_detected != "спокій":
            break

    # Визначення стилю
    style_detected = "нейтральний"
    for name, pattern in STYLES.items():
        if pattern.get("default", False):
            style_detected = name
            break

    # Формування гіпотези
    if related_thoughts:
        hypothesis = f"Це схоже на одну з моїх думок: «{related_thoughts[-1]}»"
    else:
        echo = vector_guessing(text)
        if echo:
            hypothesis = f"Можливо, ти маєш на увазі: «{echo}»"
        else:
            hypothesis = "Я поки не можу визначити, до чого це відноситься."

    result = {
        "emotion": emotion_detected,
        "style": style_detected,
        "hypothesis": hypothesis,
        "pause": EMOTIONS['emotions'].get(emotion_detected, {}).get("pause", 0.3),
        "tone": EMOTIONS['emotions'].get(emotion_detected, {}).get("tone", "спокійний"),
        "intensity": EMOTIONS['emotions'].get(emotion_detected, {}).get("intensity", "medium")
    }

    return result

def generate_intuitive_response(prompt):
    result = analyze_and_guess(prompt)
    return {
        "text": result["hypothesis"],
        "emotion": result["emotion"],
        "tone": result["tone"],
        "intensity": result["intensity"],
        "pause": result["pause"]
    }
