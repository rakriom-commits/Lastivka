
import json
from datetime import datetime
import os

MEMORY_FILE = os.path.join("lastivka_core", "config", "memory_store.json")

def load_memory():
    """Завантажити всю памʼять"""
    if not os.path.exists(MEMORY_FILE):
        return {"thoughts": []}
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def remember_thought(thought):
    """Запамʼятати нову думку з часовою міткою"""
    data = load_memory()
    if "thoughts" not in data:
        data["thoughts"] = []
    data["thoughts"].append({
        "ts": datetime.now().isoformat(),
        "text": thought
    })
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def search_memory(keyword):
    """Пошук думок за ключовим словом"""
    data = load_memory()
    return [entry for entry in data.get("thoughts", []) if keyword.lower() in entry["text"].lower()]
