import json
from pathlib import Path
from datetime import datetime

# 📁 Шлях до стилів
STYLES_PATH = Path(__file__).resolve().parent.parent / "config" / "behavioral_styles.json"
STYLE_LOG = Path(__file__).resolve().parent.parent / "logs" / "style_changes.log"

# 🧹 Завантаження стилів
def load_styles():
    try:
        with open(STYLES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                styles = {entry.get("name", f"стиль_{i}"): entry for i, entry in enumerate(data)}
                return {"default": "нейтральний", "styles": styles}
            return data
    except Exception as e:
        print(f"⚠️ Помилка завантаження стилів: {e}")
        return {"default": "нейтральний", "styles": {}}

STYLES_DATA = load_styles()
ACTIVE_STYLE = STYLES_DATA.get("default", "нейтральний")
STYLES = STYLES_DATA.get("styles", {})

def get_active_style():
    return ACTIVE_STYLE

def set_active_style(style_name: str):
    global ACTIVE_STYLE
    if style_name in STYLES:
        ACTIVE_STYLE = style_name
        log_style_change(style_name)
        print(f"🎭 Стиль змінено на: {style_name}")
        return True
    else:
        print(f"❌ Стиль '{style_name}' не знайдено.")
        return False

def get_style_behavior(style_name=None):
    style = style_name or ACTIVE_STYLE
    return STYLES.get(style, {
        "reaction_prefix": "",
        "reaction_suffix": "",
        "tone": "звичайний",
        "speed": 170,
        "style_type": "нейтральний",
        "pause": 0.4
    })

def log_style_change(style_name):
    try:
        with open(STYLE_LOG, "a", encoding="utf-8") as log:
            log.write(f"{datetime.now().isoformat()} — стиль: {style_name}\n")
    except:
        pass

def react_by_style(prompt: str):
    behavior = get_style_behavior()
    prefix = behavior.get("reaction_prefix", "")
    suffix = behavior.get("reaction_suffix", "")
    tone = behavior.get("tone", "звичайний")
    speed = behavior.get("speed", 170)
    pause = behavior.get("pause", 0.3)

    styled_response = f"{prefix}{prompt}{suffix}"
    return styled_response, tone, speed, pause