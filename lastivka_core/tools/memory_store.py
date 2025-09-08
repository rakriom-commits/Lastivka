# -*- coding: utf-8 -*-
# lastivka_core/tools/memory_store.py
from pathlib import Path
from datetime import datetime, timedelta
import json
import logging
from tools.emotion_engine import EmotionEngine

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[
        logging.FileHandler("C:/Lastivka/lastivka_core/logs/memory_store.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# === Fallback-файл для ЛОГІВ (legacy) ===
LEGACY_MEMORY_FILE = Path(__file__).resolve().parents[1] / "logs" / "memory_store.json"
LEGACY_MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)

# Команди пам'яті, які НЕ мають перехоплюватись тригерами
MEMORY_COMMAND_MARKERS = (
    "запам’ятай:", "запам'ятай:", "запамятай:",
    "що ти пам’ятаєш про", "що ти пам'ятаєш про",
    "думки", "пам’ять", "пам'ять", "спогади",
)

# === Гнучке підключення до основного менеджера памʼяті ===
try:
    from main.memory_manager import memory as _MEM
except ImportError:
    try:
        from memory_manager import memory as _MEM
    except ImportError:
        _MEM = None

# Ініціалізація EmotionEngine
emotion_engine = EmotionEngine()

def _ensure_legacy_file():
    if not LEGACY_MEMORY_FILE.exists():
        default_memory = {"thoughts": [], "triggers": {}}
        LEGACY_MEMORY_FILE.write_text(json.dumps(default_memory, ensure_ascii=False, indent=2), encoding="utf-8")

def load_memory():
    """Legacy: читає /logs/memory_store.json."""
    _ensure_legacy_file()
    try:
        data = json.loads(LEGACY_MEMORY_FILE.read_text(encoding="utf-8") or "{}")
        if not isinstance(data, dict):
            raise json.JSONDecodeError("Невірний формат JSON", doc=str(data), pos=0)
        data.setdefault("thoughts", [])
        data.setdefault("triggers", {})
        return data
    except json.JSONDecodeError as e:
        raise e

def save_memory(memory):
    """Legacy: пише у /logs/memory_store.json."""
    LEGACY_MEMORY_FILE.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")

def log_thought(thought):
    """Legacy: дублює «швидкі думки» у /logs."""
    memory = load_memory()
    record = {"ts": datetime.now().isoformat(), "text": thought}
    memory.setdefault("thoughts", []).append(record)
    save_memory(memory)

def recall_memory():
    memory = load_memory()
    thoughts = memory.get("thoughts", [])
    if thoughts:
        return thoughts[-1].get("text", "")
    return None

def search_memories(text):
    memory = load_memory()
    text = (text or "").lower()
    results = []
    for section, entries in memory.items():
        entries = [entries] if isinstance(entries, dict) else (entries or [])
        for entry in entries:
            if isinstance(entry, dict):
                value = str(entry.get("text") or entry.get("value") or "")
                if text and text in value.lower():
                    results.append(f"[{section}] {value}")
    return "\n".join(results) if results else "[⛔️] Нічого не знайдено."

def summarize_memories():
    memory = load_memory()
    summary = {}
    for key, val in memory.items():
        summary[key] = (len(val) if isinstance(val, list) else 1)
    lines = [f"{section.capitalize()}: {count}" for section, count in summary.items()]
    return "🧾 Зведення памʼяті:\n" + "\n".join(lines) if lines else "[⛔️] Памʼять порожня."

def recall_from_question(question):
    def normalize(word):
        word = (word or "").lower()
        for ending in ["и", "і", "я", "ю", "є", "о", "у", "е"]:
            if word.endswith(ending):
                return word[:-1]
        return word
    q = normalize(question)
    memory = load_memory()
    found = []
    for section, entries in memory.items():
        entries = [entries] if isinstance(entries, dict) else (entries or [])
        for entry in entries:
            if isinstance(entry, dict):
                value = str(entry.get("text") or entry.get("value") or "")
                if q and q in normalize(value):
                    found.append(f"[{section}] {value}")
    return "\n".join(found) if found else "🙈 Нічого подібного не згадується..."

def purge_old_thoughts(days=30):
    memory = load_memory()
    thoughts = memory.get("thoughts", []) or []
    threshold = datetime.now() - timedelta(days=days)
    filtered = []
    for entry in thoughts:
        try:
            ts = datetime.fromisoformat(entry.get("ts", ""))
            if ts >= threshold:
                filtered.append(entry)
        except Exception:
            continue
    if len(filtered) != len(thoughts):
        memory["thoughts"] = filtered
        save_memory(memory)
        return f"🧹 Очищено {len(thoughts) - len(filtered)} застарілих записів думок."
    return "✅ Очищення не потребувалося."

def _normalize_trigger_response(response):
    """Уніфікація відповіді тригера до словника."""
    if isinstance(response, dict) and "text_to_say" in response:
        resp = dict(response)
        resp.setdefault("log_text", f"📊 тригер: {resp['text_to_say']}")
        resp.setdefault("tone", "нейтральний")
        resp.setdefault("speed", 180)
        resp.setdefault("intensity", 0.3)
        return resp
    if isinstance(response, tuple):
        text = str(response[0]) if response else ""
    else:
        text = str(response)
    text_clean = text.strip().lstrip("📊").strip()
    return {
        "text_to_say": text_clean,
        "log_text": f"📊 тригер: {text_clean}",
        "tone": "нейтральний",
        "speed": 180,
        "intensity": 0.3,
    }

def check_triggers(input_text):
    """Повертає словник: {text_to_say, log_text, tone, speed, intensity} або None."""
    txt = (input_text or "").strip().lower()
    # Ігноруємо команди пам'яті
    if any(marker in txt for marker in MEMORY_COMMAND_MARKERS):
        return None
    # Перевірка емоційних тригерів через EmotionEngine
    detected = emotion_engine.detect_emotion(txt)
    if detected["emotion"]:
        return _normalize_trigger_response({
            "text_to_say": detected["reaction"],
            "log_text": f"📊 емоція: {detected['emotion']}",
            "tone": detected["tone"],
            "speed": detected["speed"],
            "intensity": detected["intensity"]
        })
    # Fallback: тригери з memory_manager або legacy
    try:
        if _MEM is not None:
            triggers = _MEM.get_triggers()
        else:
            legacy = load_memory()
            triggers = legacy.get("triggers", {}) or {}
        logger.debug(f"[DEBUG]: Triggers checked: {triggers}")
        for key, response in triggers.items():
            key_l = (key or "").lower()
            if key_l and key_l in txt:
                logger.debug(f"[DEBUG]: Trigger matched: {key} -> {response}")
                return _normalize_trigger_response(response)
    except Exception as e:
        logger.error(f"[ERROR] Помилка перевірки тригерів: {e}")
    return None