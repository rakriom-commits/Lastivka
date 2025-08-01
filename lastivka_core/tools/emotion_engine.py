# tools/emotion_engine.py
import json
from pathlib import Path

EMOTION_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "emotion_config.json"

# поточний стан емоції (для глобальних викликів set_emotion)
_current = {
    "emotion": "спокій",
    "reaction": "",
    "speed": 170,
    "tone": "нейтральний",
    "intensity": "medium"
}

def _load_cfg():
    """Завантажує конфіг емоцій. Підтримує дві схеми:
       1) {"emotions": {...}, "speed": {...}}
       2) {...емоції в корені..., "speed": {...}}"""
    with open(EMOTION_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Емоції можуть бути в корені або під ключем "emotions"
    raw_emotions = cfg.get("emotions", cfg)
    speeds = cfg.get("speed", {})
    default_speed = speeds.get("default", 170)

    # нормалізуємо ключі емоцій до нижнього регістру
    emotions = {}
    for k, v in raw_emotions.items():
        if isinstance(v, dict):
            emotions[k.lower()] = v

    return emotions, speeds, default_speed


class EmotionEngine:
    """Сумісний клас: detect_emotion(message) повертає структуру з полями:
       emotion, reaction, speed, tone, intensity."""
    def __init__(self, config_path: Path = None):
        global EMOTION_CONFIG_PATH
        if config_path is not None:
            EMOTION_CONFIG_PATH = Path(config_path)
        self._emotions, self._speeds, self._default_speed = _load_cfg()

    def detect_emotion(self, message: str):
        detected = {
            "emotion": None,
            "reaction": None,
            "speed": self._default_speed,
            "tone": "нейтральний",
            "intensity": "medium"
        }
        if not message:
            return detected

        msg = message.lower()
        for name_lc, props in self._emotions.items():
            triggers = props.get("triggers", [])
            for trig in triggers:
                if isinstance(trig, str) and trig.lower() in msg:
                    # відновлюємо «людську» назву (може відрізнятися регістром)
                    name = name_lc
                    return {
                        "emotion": name,
                        "reaction": props.get("reaction", ""),
                        "speed": self._speeds.get(name, self._speeds.get(name_lc, self._default_speed)),
                        "tone": props.get("tone", "нейтральний"),
                        "intensity": props.get("intensity", "medium")
                    }
        return detected


# --- Глобальні утиліти для простих викликів з інших модулів (file_watcher тощо) ---

def set_emotion(name: str):
    """Встановлює глобальний емоційний стан за назвою (нечутлива до регістру)."""
    global _current
    if not name:
        return
    try:
        emotions, speeds, default_speed = _load_cfg()
        key = name.lower()
        props = emotions.get(key)
        if not props:
            print(f"❌ Емоція '{name}' не знайдена. Доступні: {', '.join(emotions.keys())}")
            return
        _current = {
            "emotion": name,
            "reaction": props.get("reaction", ""),
            "speed": speeds.get(name, speeds.get(key, default_speed)),
            "tone": props.get("tone", "нейтральний"),
            "intensity": props.get("intensity", "medium")
        }
        print(f"💫 Емоція оновлена: {name} ({_current['tone']})")
    except Exception as e:
        print(f"❌ Помилка при оновленні емоції: {e}")

def get_emotion():
    return _current

def list_emotions():
    try:
        emotions, _, _ = _load_cfg()
        return list(emotions.keys())
    except Exception:
        return []
