import json
import os
from datetime import datetime

LOG_FILE = os.path.join(
    os.path.dirname(__file__), "experience_log.json"
)

def load_experiences() -> list[dict]:
    """Завантажує всі записи короткочасного досвіду."""
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def add_experience(last_action: str, thought: str, entry_type: str = "internal") -> None:
    """Додає новий запис у досвід."""
    log = load_experiences()
    log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "last_action": last_action,
        "thought": thought,
        "entry_type": entry_type
    })
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

def filter_by_type(entry_type: str) -> list[dict]:
    """Фільтрує записи за типом (dialogue_based, internal, reflection)."""
    log = load_experiences()
    return [entry for entry in log if entry.get("entry_type") == entry_type]
