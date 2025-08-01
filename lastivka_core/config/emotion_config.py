import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "emotion_config.json"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    loaded = json.load(f)

# 🔒 Захист: якщо раптом знову список — обгорнути в словник
if isinstance(loaded, list):
    EMOTIONS = {
        "emotions": {
            entry.get("name", f"емоція_{i}"): {
                "triggers": entry.get("words", []),
                "reaction": entry.get("reaction", ""),
                "tone": entry.get("tone", ""),
                "intensity": entry.get("intensity", "")
            } for i, entry in enumerate(loaded)
        },
        "speed": {"default": 170}
    }
else:
    EMOTIONS = loaded

# 🧠 Додано функцію визначення емоції
def detect_emotion(text):
    text_lower = text.lower()
    for emotion_name, data in EMOTIONS["emotions"].items():
        triggers = data.get("triggers", [])
        if any(word.lower() in text_lower for word in triggers):
            return emotion_name
    return "спокій"
