import json
import os

REFLECTION_FILE = os.path.join(
    os.path.dirname(__file__), "lastivka_reflections.json"
)

def load_reflections() -> dict:
    """Завантажує усі категорії рефлексій."""
    if not os.path.exists(REFLECTION_FILE):
        return {}
    with open(REFLECTION_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_reflections(category: str) -> list[str]:
    """Повертає список рефлексій за категорією."""
    reflections = load_reflections()
    return reflections.get(category, [])

def list_categories() -> list[str]:
    """Повертає перелік категорій."""
    reflections = load_reflections()
    return list(reflections.keys())
