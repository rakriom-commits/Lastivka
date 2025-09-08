# lastivka_core/tools/short_memory.py

import json
from datetime import datetime
import os

# 📍 Тепер памʼять зберігається у окремому файлі
DEFAULT_MEMORY_FILE = os.path.join("lastivka_core", "config", "short_memory.json")

def load_memory(path: str = DEFAULT_MEMORY_FILE):
    """Завантажити всю буферну памʼять з файлу"""
    if not os.path.exists(path):
        return {"thoughts": []}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"thoughts": []}

def remember_thought(thought: str, path: str = DEFAULT_MEMORY_FILE):
    """Запамʼятати нову думку з часовою міткою"""
    data = load_memory(path)
    if "thoughts" not in data:
        data["thoughts"] = []
    data["thoughts"].append({
        "ts": datetime.now().isoformat(),
        "text": thought
    })
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def recall_thought(path: str = DEFAULT_MEMORY_FILE):
    """Повертає останню збережену думку як текст, або None"""
    data = load_memory(path)
    thoughts = data.get("thoughts", [])
    if not thoughts:
        return None
    return thoughts[-1]["text"]

def search_memory(keyword: str, path: str = DEFAULT_MEMORY_FILE):
    """Пошук думок за ключовим словом"""
    data = load_memory(path)
    return [entry for entry in data.get("thoughts", []) if keyword.lower() in entry["text"].lower()]

def clear_short_memory(path: str = DEFAULT_MEMORY_FILE):
    """Очистити всю буферну памʼять"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"thoughts": []}, f, ensure_ascii=False, indent=2)

__all__ = ["remember_thought", "recall_thought", "load_memory", "search_memory", "clear_short_memory"]
