import difflib
from main.memory_store import list_memories
from config.emotion_config import EMOTIONS
from config.behavioral_styles import STYLES


def normalize_text(text):
    return str(text).lower().strip().replace("’", "'").replace("  ", " ")

def vector_guessing(prompt):
    """Аналіз збігу з думками за слабкими ключовими словами та відлуннями контексту."""
    text = normalize_text(prompt)
    memory = list_memories("думка")
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
    thoughts = memory.get("думка", []) if isinstance(memory, dict) else []

    related_thoughts = []
    for t in thoughts:
        value = ""
        if isinstance(t, dict):
            value = str(t.get("value", ""))
        elif isinstance(t, str):
            value = t
        if value and difflib.SequenceMatcher(None, text, value.lower()).ratio() > 0.6:
            related_thoughts.append(value)

    # 🧠 Визначення емоції
    emotion_detected = "спокій"
    for emotion_name, entry in EMOTIONS.get("emotions", {}).items():
        for word in entry.get("triggers", []):
            if word.lower() in text:
                emotion_detected = emotion_name
                break
        if emotion_detected != "спокій":
            break

    # 🎭 Визначення стилю
    style_detected = "стратег"
    for name, pattern in STYLES.items():
        if pattern.get("активний", False):
            style_detected = name
            break

    # 🔮 Формування припущення
    if related_thoughts:
        hypothesis = f"Це схоже на одну з твоїх думок: «{related_thoughts[-1]}»"
    else:
        echo = vector_guessing(text)
        if echo:
            hypothesis = f"Є слабка подібність до думки: «{echo}»"
        else:
            hypothesis = "Можливо, ти маєш на увазі щось глибше або пов’язане з попереднім досвідом."

    result = {
        "емоція": emotion_detected,
        "стиль": style_detected,
        "припущення": hypothesis,
        "pause": EMOTIONS["emotions"].get(emotion_detected, {}).get("pause", 0.3),
        "tone": EMOTIONS["emotions"].get(emotion_detected, {}).get("tone", "гладкий"),
        "intensity": EMOTIONS["emotions"].get(emotion_detected, {}).get("intensity", "medium")
    }

    return result

def generate_intuitive_response(prompt):
    result = analyze_and_guess(prompt)
    return {
        "text": result["припущення"],
        "emotion": result["емоція"],
        "tone": result["tone"],
        "intensity": result["intensity"],
        "pause": result["pause"]
    }
