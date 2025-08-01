import json
from pathlib import Path
from datetime import datetime

MEMORY_FILE = Path(__file__).resolve().parent / "memory_store.json"
ARCHIVE_FILE = Path(__file__).resolve().parent / "memory_archive.json"

def load_memory():
    if not MEMORY_FILE.exists():
        return {}
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

def archive_memory():
    memory = load_memory()
    if memory:
        archive = {"archived_at": datetime.now().isoformat(), "data": memory}
        with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
            json.dump(archive, f, ensure_ascii=False, indent=2)

def remember(key, value, tone="базова"):
    memory = load_memory()
    record = {
        "value": value,
        "timestamp": datetime.now().isoformat(),
        "tone": tone
    }
    if key in memory:
        if isinstance(memory[key], list):
            memory[key].append(record)
        else:
            memory[key] = [memory[key], record]
    else:
        memory[key] = [record]
    save_memory(memory)

def recall(key):
    memory = load_memory()
    return memory.get(key)

def forget(key):
    memory = load_memory()
    if key in memory:
        del memory[key]
        save_memory(memory)

def list_memories():
    return load_memory()

def recall_from_question(question):
    question = question.lower()
    memory = load_memory()

    for k, v in memory.items():
        if question in k.lower():
            return v

    for k, v in memory.items():
        if isinstance(v, list):
            for item in v:
                if isinstance(item, dict) and question in item.get("value", "").lower():
                    return f"{k} → {item['value']}"

    return None
