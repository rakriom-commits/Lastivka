# -*- coding: utf-8 -*-
import json
from pathlib import Path
import logging
from main.style_manager import auto_adjust_style_from_emotion

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[
        logging.FileHandler("C:/Lastivka/lastivka_core/logs/emotion.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# Шляхи
BASE_DIR = Path(__file__).resolve().parent.parent
EMOTION_CONFIG_PATH = BASE_DIR / "config" / "emotion_config.json"
DETECTED_PATH = BASE_DIR / "logs" / "detected_emotion.json"

# Створення директорії для логів
DETECTED_PATH.parent.mkdir(parents=True, exist_ok=True)

# Поточна емоція
_current = {
    "emotion": "спокій",
    "reaction": "",
    "speed": 170,
    "tone": "нейтральний",
    "intensity": "medium"
}

def _load_cfg():
    """Завантаження конфігурації емоцій з файлу."""
    default_config = {
        "emotions": {
            "захват": {"triggers": ["круто", "чудово"], "reaction": "Це неймовірно!", "tone": "позитивний", "intensity": "high"},
            "запал": {"triggers": ["вперед", "давай"], "reaction": "Готовий до дії!", "tone": "енергійний", "intensity": "high"},
            "спокій": {"triggers": ["ок", "нормально"], "reaction": "Все під контролем.", "tone": "нейтральний", "intensity": "medium"},
            "сум": {"triggers": ["сумно", "гірко"], "reaction": "Я з тобою, все буде добре.", "tone": "м'який", "intensity": "medium"}
        },
        "speed": {
            "захват": 180,
            "запал": 190,
            "спокій": 170,
            "сум": 150
        },
        "default_speed": 170
    }
    try:
        if not EMOTION_CONFIG_PATH.exists():
            logging.info(f"[INIT] Створюю конфігурацію: {EMOTION_CONFIG_PATH}")
            with EMOTION_CONFIG_PATH.open("w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            return default_config["emotions"], default_config["speed"], default_config["default_speed"]
        with EMOTION_CONFIG_PATH.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
        raw_emotions = cfg.get("emotions", cfg)
        speeds = cfg.get("speed", {})
        default_speed = cfg.get("default_speed", 170)
        emotions = {k.lower(): v for k, v in raw_emotions.items() if isinstance(v, dict)}
        return emotions, speeds, default_speed
    except Exception as e:
        logging.error(f"[ERROR] Помилка завантаження {EMOTION_CONFIG_PATH}: {e}")
        return default_config["emotions"], default_config["speed"], default_config["default_speed"]

class EmotionEngine:
    """Модуль розпізнавання емоцій: detect_emotion(message) повертає
       emotion, reaction, speed, tone, intensity."""
    def __init__(self, config_path: Path = None):
        global EMOTION_CONFIG_PATH
        if config_path is not None:
            EMOTION_CONFIG_PATH = Path(config_path)
        try:
            self._emotions, self._speeds, self._default_speed = _load_cfg()
        except Exception as e:
            logging.error(f"[ERROR] Не вдалося ініціалізувати EmotionEngine: {e}")
            self._emotions, self._speeds, self._default_speed = {}, {}, 170

    def detect_emotion(self, message: str):
        global _current
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
                    name = name_lc
                    detected = {
                        "emotion": name,
                        "reaction": props.get("reaction", ""),
                        "speed": self._speeds.get(name, self._speeds.get(name_lc, self._default_speed)),
                        "tone": props.get("tone", "нейтральний"),
                        "intensity": props.get("intensity", "medium")
                    }
                    _current = detected
                    try:
                        with DETECTED_PATH.open("w", encoding="utf-8") as f:
                            json.dump(_current, f, ensure_ascii=False, indent=2)
                        logging.info(f"[EmotionEngine] Виявлено емоцію: {name}")
                        auto_adjust_style_from_emotion()  # Виклик автоадаптації стилю
                    except Exception as e:
                        logging.error(f"[ERROR] Помилка запису detected_emotion.json: {e}")
                    return detected
        return detected

# --- Допоміжні методи для прямого задання емоції ззовні ---
def set_emotion(name: str):
    """Примусово встановлює поточну емоцію за назвою."""
    global _current
    if not name:
        return
    try:
        emotions, speeds, default_speed = _load_cfg()
        key = name.lower()
        props = emotions.get(key)
        if not props:
            logging.warning(f"⚠️ Емоція '{name}' не знайдена. Доступні: {', '.join(emotions.keys())}")
            return
        _current = {
            "emotion": name,
            "reaction": props.get("reaction", ""),
            "speed": speeds.get(name, speeds.get(key, default_speed)),
            "tone": props.get("tone", "нейтральний"),
            "intensity": props.get("intensity", "medium")
        }
        logging.info(f"✅ Емоція вручну змінена: {name} ({_current['tone']})")
        with DETECTED_PATH.open("w", encoding="utf-8") as f:
            json.dump(_current, f, ensure_ascii=False, indent=2)
        auto_adjust_style_from_emotion()  # Виклик автоадаптації стилю
    except Exception as e:
        logging.error(f"⚠️ Помилка при встановленні емоції: {e}")

def get_emotion():
    return _current

def list_emotions():
    try:
        emotions, _, _ = _load_cfg()
        return list(emotions.keys())
    except Exception:
        return []