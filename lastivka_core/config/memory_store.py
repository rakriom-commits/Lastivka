import json
from pathlib import Path
from datetime import datetime, timedelta

MEMORY_FILE = Path(__file__).resolve().parent.parent / "config" / "memory_store.json"

def load_memory():
    if not MEMORY_FILE.exists():
        default_memory = {"thoughts": [], "triggers": {}}
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(default_memory, f, ensure_ascii=False, indent=2)
        return default_memory
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                raise json.JSONDecodeError("JSON не є словником", doc=str(data), pos=0)
            return data
    except json.JSONDecodeError as e:
        raise e

def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

# 🧠 Запис думки (у список thoughts)
def log_thought(thought):
    memory = load_memory()
    record = {
        "ts": datetime.now().isoformat(),
        "text": thought
    }
    memory.setdefault("thoughts", []).append(record)
    save_memory(memory)

# 🔁 Повертає останню думку
def recall_memory():
    memory = load_memory()
    thoughts = memory.get("thoughts", [])
    if thoughts:
        return thoughts[-1].get("text", "")
    return None

# 🔍 Пошук по всіх секціях
def search_memories(text):
    memory = load_memory()
    text = text.lower()
    results = []
    for section in memory:
        entries = memory.get(section, [])
        if isinstance(entries, dict):
            entries = [entries]
        for entry in entries:
            if isinstance(entry, dict):
                value = str(entry.get("text") or entry.get("value") or "")
                if text in value.lower():
                    results.append(f"[{section}] {value}")
    return "\n".join(results) if results else "🔍 Нічого не знайдено."

# 📋 Підсумок кількості записів
def summarize_memories():
    memory = load_memory()
    summary = {}
    for key in memory:
        count = len(memory[key]) if isinstance(memory[key], list) else 1
        summary[key] = count
    lines = [f"{section.capitalize()}: {count}" for section, count in summary.items()]
    return "📊 Підсумок памʼяті:\n" + "\n".join(lines) if lines else "👭 Памʼять порожня."

# ❓ Спроба знайти щось по питанню
def recall_from_question(question):
    def normalize(word):
        word = word.lower()
        for ending in ["у", "ю", "е", "а", "о", "і", "и", "ь"]:
            if word.endswith(ending):
                word = word[:-1]
        return word

    q = normalize(question)
    memory = load_memory()
    found = []

    for section, entries in memory.items():
        if isinstance(entries, dict):
            entries = [entries]
        for entry in entries:
            value = str(entry.get("text") or entry.get("value") or "")
            if q in normalize(value):
                found.append(f"[{section}] {value}")
    return "\n".join(found) if found else "🔍 Я не знайшла нічого в памʼяті, що стосувалося б цього питання."

# 🧹 Видалення думок старших за N днів
def purge_old_thoughts(days=30):
    memory = load_memory()
    thoughts = memory.get("thoughts", [])
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
        return f"🧹 Видалено {len(thoughts) - len(filtered)} старих думок."
    return "✅ Думки актуальні, нічого не видалено."

# 🚨 Перевірка на тригери у введенні
def check_triggers(input_text):
    memory = load_memory()
    triggers = memory.get("triggers", {})
    for key, response in triggers.items():
        if key.lower() in input_text.lower():
            return response
    return None
