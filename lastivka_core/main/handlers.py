# -*- coding: utf-8 -*-
"""
Handlers: маршрути простих команд пам'яті (сумісно з новою структурою).
"""

try:
    from memory.manager import MEMORY as memory
except Exception:
    try:
        from memory.manager import MemoryManager
        memory = MemoryManager()
    except Exception:
        memory = None

import re
import logging
logger = logging.getLogger(__name__)

def _clean(s: str) -> str:
    return (s or "").strip().strip(' "\'“”«»').lower()

def _split_key_val(body: str):
    body = (body or "").strip()
    m2 = re.search(r"^(?P<key>[^=:–—\-]+?)\s*[:=\-–—]\s*(?P<val>.+)$", body)
    if m2:
        return (m2.group("key") or "").strip(), (m2.group("val") or "").strip()
    m3 = re.search(r"^(?P<key>[^=:–—\-]+?)\s+це\s+(?P<val>.+)$", body, flags=re.I)
    if m3:
        return (m3.group("key") or "").strip(), (m3.group("val") or "").strip()
    return None, None

def handle_save_command(user_text: str):
    if memory is None:
        return "Пам'ять недоступна."
    txt = (user_text or "").strip()
    m = re.search(r"запам[’']?ятай\s*:\s*(.+)", txt, flags=re.I)
    if not m: return None
    body = m.group(1).strip()
    key, val = _split_key_val(body)
    if key and val:
        try:
            memory.delete_thoughts_by_key(key)
        except Exception:
            logger.exception("delete_thoughts_by_key failed")
        memory.add_thought(key, val, tone="впевнений", tags=["manual"])
        return {
            "text_to_say": f"Я запамʼятала: {key} — {val}",
            "log_text":    f"[MEMORY]: запамʼятала: {key} = {val}",
            "tone": "впевнений", "speed": 180, "intensity": 0.35
        }
    memory.add_thought("думка", body, tone="впевнений", tags=["manual"])
    return {
        "text_to_say": f"Я запамʼятала: {body}",
        "log_text":    f"[MEMORY]: запамʼятала: {body}",
        "tone": "впевнений", "speed": 180, "intensity": 0.35
    }

def handle_recall_command(user_text: str):
    if memory is None:
        return "Пам'ять недоступна."
    txt = _clean(user_text)
    patterns = [
        r"що\s+ти\s+пам[’']?ятаєш\s+про\s+(?P<key>.+)$",
        r"що\s+я\s+(?:тобі\s+)?казав\s+про\s+(?P<key>.+)$",
        r"що\s+я\s+(?:тобі\s+)?говорив\s+про\s+(?P<key>.+)$",
        r"що\s+я\s+казав\s+тобі\s+про\s+(?P<key>.+)$",
        r"що\s+я\s+говорив\s+тобі\s+про\s+(?P<key>.+)$",
        r"що\s+я\s+(?:тобі\s+)?розповідав\s+про\s+(?P<key>.+)$",
        r"що\s+я\s+(?:тобі\s+)?розказував\s+про\s+(?P<key>.+)$",
        r"що\s+я\s+(?:тобі\s+)?казала\s+про\s+(?P<key>.+)$",
        r"що\s+я\s+(?:тобі\s+)?говорила\s+про\s+(?P<key>.+)$",
    ]
    for pat in patterns:
        m = re.search(pat, txt, flags=re.I)
        if not m: continue
        raw_key = m.group("key")
        key = _clean(re.sub(r"[?\.!]+$", "", raw_key))
        if not key: break
        thoughts = memory.get_thoughts_by_key(key)
        if not thoughts:
            return {
                "text_to_say": f"Я поки нічого не зберігала про «{key}».",
                "log_text":    f"[MEMORY]: спогадів нема по ключу «{key}»",
                "tone": "спокійний", "speed": 170, "intensity": 0.25
            }
        seen_vals, items = set(), []
        for t in reversed(thoughts):
            v = (t.get("text") or "").strip()
            key_norm = f"{key}:{v}".lower()
            if v and key_norm not in seen_vals:
                seen_vals.add(key_norm); items.append(v)
            if len(items) >= 10: break
        spoken = "; ".join(items)
        return {
            "text_to_say": f"Я памʼятаю таке про {key}: {spoken}",
            "log_text":    f"[MEMORY]: спогади про {key}: {len(items)}",
            "tone": "впевнений", "speed": 180, "intensity": 0.3
        }
    return None

def handle_all_memory_command(user_text: str):
    if memory is None:
        return "Пам'ять недоступна."
    txt = _clean(user_text)
    if txt not in {"думки", "памʼять", "пам'ять", "память", "спогади", "memory"}:
        return None
    data = memory.get_all_memory()
    seen, items = set(), []
    for k, arr in (data or {}).items():
        if k == "triggers": continue
        if isinstance(arr, list):
            for rec in arr:
                t = (rec or {}).get("text")
                if not t: continue
                line = f"{k}: {t}"
                key_norm = line.strip().lower()
                if key_norm not in seen:
                    seen.add(key_norm); items.append(line)
    text = "; ".join(items[:20]) if items else "Памʼять порожня."
    return {
        "text_to_say": text,
        "log_text":    f"[MEMORY]: думки (унікальні): {text}",
        "tone": "впевнений", "speed": 180, "intensity": 0.3
    }

# === Експорт для тестів та ядра ===
COMMANDS = {
    "save": handle_save_command,
    "recall": handle_recall_command,
    "all_memory": handle_all_memory_command,
}

def handle_intents(user_text: str):
    for name, func in COMMANDS.items():
        try:
            result = func(user_text)
            if result:
                return result
        except Exception as e:
            logger.exception(f"Handler {name} failed: {e}")
    return None

def handle_memory_commands(user_text: str):
    return (
        handle_save_command(user_text)
        or handle_recall_command(user_text)
        or handle_all_memory_command(user_text)
    )
