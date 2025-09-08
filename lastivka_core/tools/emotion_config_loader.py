# emotion_config_loader.py
import json
from pathlib import Path

# Шлях до конфігурації емоцій
CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "emotion_config.json"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    loaded = json.load(f)

# Якщо емоції у вигляді списку — перетворити в словник
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

# Визначення емоції за ключовими словами в тексті
def detect_emotion(text: str) -> str:
    text_lower = (text or "").lower()
    for emotion_name, data in EMOTIONS.get("emotions", {}).items():
        triggers = data.get("triggers", []) or []
        if any((word or "").lower() in text_lower for word in triggers):
            return emotion_name
    return "спокій"