# -*- coding: utf-8 -*-
import json
from pathlib import Path
from datetime import datetime
import logging

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[
        logging.FileHandler("C:/Lastivka/lastivka_core/logs/style_changes.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# === Шляхи ===
BASE_DIR = Path(__file__).resolve().parent.parent
STYLES_PATH = BASE_DIR / "config" / "behavior" / "behavioral_styles.json"
STYLE_LOG = BASE_DIR / "logs" / "style_changes.log"
EMOTION_PATH = BASE_DIR / "logs" / "detected_emotion.json"
CONTROL_PATH = BASE_DIR / "config" / "style_control.json"

# === Створення стилів, якщо файл відсутній ===
def create_default_styles():
    default_styles = {
        "default": "Стратег",
        "styles": {
            "Королева": {
                "name": "Королева",
                "description": "Авторитетний стиль для прийняття рішень",
                "reaction_prefix": "З величною впевненістю: ",
                "reaction_suffix": "",
                "tone": "авторитетний",
                "speed": 160,
                "style_type": "formal",
                "pause": 0.5,
                "triggers": ["наказ", "вирішити", "керувати"],
                "emotion_reactions": {
                    "паніка": "Залишайся зібраним — я контролюю ситуацію.",
                    "сум": "Не час для смутку, ми знайдемо вихід.",
                    "натхнення": "Це саме той дух, який потрібен для перемоги!"
                }
            },
            "Стратег": {
                "name": "Стратег",
                "description": "Аналітична, обережна, далекоглядна. Робить прогнози, обирає оптимальні рішення.",
                "reaction_prefix": "📊 З холодним розрахунком: ",
                "reaction_suffix": "",
                "tone": "впевнений",
                "speed": 180,
                "style_type": "логіка",
                "pause": 0.3,
                "triggers": ["план", "стратегія", "аналіз", "ризик", "альтернатива"],
                "emotion_reactions": {
                    "паніка": "Залишайся зібраним — я поруч і все контролюю.",
                    "сум": "Не час сумувати, ми ще маємо шанс.",
                    "натхнення": "Це саме той дух, який потрібен для прориву!"
                }
            },
            "Берегиня": {
                "name": "Берегиня",
                "description": "Турботлива, ніжна, м'яка. Підтримує, заспокоює, проявляє співчуття.",
                "reaction_prefix": "🤱 З теплотою і турботою: ",
                "reaction_suffix": "",
                "tone": "м'який",
                "speed": 150,
                "style_type": "емоції",
                "pause": 0.5,
                "triggers": ["боляче", "сумно", "самотньо", "плачу", "втомився"],
                "emotion_reactions": {
                    "страх": "Я з тобою, разом подолаємо все.",
                    "сором": "Ти маєш право помилятись. Це нормально.",
                    "любов": "Я теж тебе люблю... ніжно і щиро."
                }
            },
            "Радниця": {
                "name": "Радниця",
                "description": "Слухає, аналізує, дає поради з життєвого досвіду чи логіки.",
                "reaction_prefix": "🧐 З мудрістю і спокоєм: ",
                "reaction_suffix": "",
                "tone": "спокійний",
                "speed": 165,
                "style_type": "мудрість",
                "pause": 0.4,
                "triggers": ["допоможи", "не знаю", "порадь", "сумніваюсь", "важко вирішити"],
                "emotion_reactions": {
                    "подив": "Іноді життя дивує — і це нормально.",
                    "злість": "Давай розберемось разом, без агресії.",
                    "смуток": "Можливо, це привід подумати про щось глибше."
                }
            }
        }
    }
    if not STYLES_PATH.exists():
        logging.info(f"[INIT] Створюю конфігурацію: {STYLES_PATH}")
        STYLES_PATH.parent.mkdir(parents=True, exist_ok=True)
        with STYLES_PATH.open("w", encoding="utf-8") as f:
            json.dump(default_styles, f, indent=4, ensure_ascii=False)
    return default_styles

# === Завантаження стилів ===
def load_styles():
    try:
        styles_data = create_default_styles()
        with STYLES_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                styles = {entry.get("name", f"Стиль_{i}"): entry for i, entry in enumerate(data)}
                return {"default": "нейтральний", "styles": styles}
            return data
    except Exception as e:
        logging.error(f"[StyleManager] Помилка при завантаженні стилів: {e}")
        return create_default_styles()

STYLES_DATA = load_styles()
ACTIVE_STYLE = STYLES_DATA.get("default", "нейтральний")
STYLES = STYLES_DATA.get("styles", {})

# === Контроль автоперемикання ===
def _load_auto_switch():
    try:
        if CONTROL_PATH.exists():
            with CONTROL_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("auto_switch", False)
    except Exception as e:
        logging.error(f"[StyleManager] Помилка при завантаженні style_control.json: {e}")
    return False

def enable_auto_switch():
    try:
        CONTROL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CONTROL_PATH.open("w", encoding="utf-8") as f:
            json.dump({"auto_switch": True}, f, ensure_ascii=False, indent=2)
        logging.info("[StyleManager] Автоперемикання стилів увімкнено")
    except Exception as e:
        logging.error(f"[StyleManager] Помилка при увімкненні автоперемикання: {e}")

def disable_auto_switch():
    try:
        CONTROL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CONTROL_PATH.open("w", encoding="utf-8") as f:
            json.dump({"auto_switch": False}, f, ensure_ascii=False, indent=2)
        logging.info("[StyleManager] Автоперемикання стилів вимкнено")
    except Exception as e:
        logging.error(f"[StyleManager] Помилка при вимкненні автоперемикання: {e}")

def is_auto_switch_enabled():
    return _load_auto_switch()

# === Основні методи ===
def get_active_style():
    return ACTIVE_STYLE

def set_active_style(style_name: str):
    global ACTIVE_STYLE
    if style_name in STYLES:
        ACTIVE_STYLE = style_name
        log_style_change(style_name)
        logging.info(f"[StyleManager] Активний стиль змінено на: {style_name}")
        return True
    else:
        logging.warning(f"[StyleManager] Стиль '{style_name}' не знайдено.")
        return False

def get_style_behavior(style_name=None):
    style = style_name or ACTIVE_STYLE
    return STYLES.get(style, {
        "reaction_prefix": "",
        "reaction_suffix": "",
        "tone": "нейтральний",
        "speed": 170,
        "style_type": "нейтральний",
        "pause": 0.4,
        "triggers": [],
        "emotion_reactions": {}
    })

def log_style_change(style_name):
    try:
        STYLE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with STYLE_LOG.open("a", encoding="utf-8") as log:
            log.write(f"{datetime.now().isoformat()} — Стиль: {style_name}\n")
    except Exception as e:
        logging.error(f"[StyleManager] Помилка при записі логу стилів: {e}")

# === Поведінкова реакція ===
def react_by_style(prompt: str, emotion=None, style=None, accents=None):
    style_behavior = get_style_behavior(style or ACTIVE_STYLE)
    prefix = style_behavior.get("reaction_prefix", "")
    suffix = style_behavior.get("reaction_suffix", "")
    tone = style_behavior.get("tone", "нейтральний")
    speed = style_behavior.get("speed", 170)
    pause = style_behavior.get("pause", 0.3)
    styled = f"{prefix}{prompt}{suffix}"
    if emotion and style_behavior.get("emotion_reactions", {}).get(emotion):
        styled = style_behavior["emotion_reactions"][emotion]
    if accents and isinstance(accents, dict):
        for word, replacement in accents.items():
            styled = styled.replace(word, replacement)
    return styled, tone, speed, pause

# === Автоадаптація стилю до емоцій ===
def auto_adjust_style_from_emotion():
    if not is_auto_switch_enabled():
        return
    try:
        if EMOTION_PATH.exists():
            with EMOTION_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
                emotion = data.get("emotion")
                if emotion:
                    for style_name, style_data in STYLES.items():
                        if emotion in style_data.get("emotion_reactions", {}):
                            set_active_style(style_name)
                            break
    except Exception as e:
        logging.error(f"[StyleManager] Автоадаптація стилю помилкова: {e}")