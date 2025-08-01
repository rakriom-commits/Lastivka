import json
from pathlib import Path

EMOTION_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "emotion_config.json"

current_emotion = {
    "emotion": "спокій",
    "reaction": "",
    "speed": 170,
    "tone": "нейтральний",
    "intensity": "medium"
}

def _load_emotions():
    with open(EMOTION_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    # підтримка двох структур: {"emotions": {...}} або все в корені
    emotions_dict = cfg.get("emotions", cfg)
    # швидкості окремо
    speeds = cfg.get("speed", {})
    default_speed = speeds.get("default", 170)
    return emotions_dict, speeds, default_speed

def set_emotion(emotion_name: str):
    global current_emotion
    try:
        emotions, speeds, default_speed = _load_emotions()
        props = emotions.get(emotion_name)
        if not props:
            print(f"❌ Емоція '{emotion_name}' не знайдена. Доступні: {', '.join(k for k in emotions.keys() if isinstance(emotions[k], dict))}")
            return
        current_emotion = {
            "emotion": emotion_name,
            "reaction": props.get("reaction", ""),
            "speed": speeds.get(emotion_name, default_speed),
            "tone": props.get("tone", "нейтральний"),
            "intensity": props.get("intensity", "medium")
        }
        print(f"💫 Емоція оновлена: {emotion_name} ({current_emotion['tone']})")
    except Exception as e:
        print(f"❌ Помилка при оновленні емоції: {e}")

def get_emotion():
    return current_emotion
