# -*- coding: utf-8 -*-
# lastivka_core/speech/stress_tools.py
"""
Утиліти наголосу:
- Дані у JSON: lastivka_core/config/voice/stress_dict.json
- Читання напряму з файлу (без кешу), щоб зміни підхоплювались одразу
- Автонормалізація латинських áéíóú → кириличні з комбінованим наголосом (а́ е́ і́ о́ у́)
"""

from __future__ import annotations
import json, re
from pathlib import Path
from typing import Dict, Iterable, Any
from lastivka_core.config.system.loader import CONFIG_ROOT

_STRESS_JSON_REL = "voice/stress_dict.json"
_RESERVED_KEYS = {"stress_overrides", "rules"}

__all__ = [
    "load_stress_dict", "save_stress_dict",
    "apply_stress_marks", "add_to_stress_dict", "add_bulk_to_stress_dict",
    "remove_from_stress_dict", "log_unknown_word", "clean_stress_dict",
    "log_unknown_words_in", "retokenize_unknown_log",
    "build_stress_todo", "import_stress_todo",
]

# Латинські наголошені → кирилиця з комбінованим акцентом U+0301
_ACCENT_FIX = {
    "á": "а́", "Á": "А́",
    "é": "е́", "É": "Е́",
    "í": "і́", "Í": "І́",
    "ó": "о́", "Ó": "О́",
    "ú": "у́", "Ú": "У́",
}
def _normalize_accent(s: str) -> str:
    return "".join(_ACCENT_FIX.get(ch, ch) for ch in s)

def _stress_dict_path() -> Path:
    p = (CONFIG_ROOT / _STRESS_JSON_REL).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _read_json_fresh(path: Path) -> Any:
    try:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        return json.loads(raw)
    except Exception:
        return {}

def _maybe_parse_json_string(val: Any) -> Any:
    if isinstance(val, str):
        s = val.strip()
        if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
            try:
                return json.loads(s)
            except Exception:
                return val
    return val

def _sanitize(raw: Any) -> Dict[str, str]:
    """
    Приводить довільну структуру до плоского {слово: наголошена_форма}.
    - Ігнорує не-рядкові значення.
    - Для reserved ключів (stress_overrides/rules) намагається злити dict у мапу.
    - Нормалізує латинські наголоси у значеннях.
    """
    out: Dict[str, str] = {}
    if not isinstance(raw, dict):
        return out
    for k, v in raw.items():
        if k in _RESERVED_KEYS:
            v2 = _maybe_parse_json_string(v)
            if isinstance(v2, dict):
                for w, s in v2.items():
                    if isinstance(w, str) and isinstance(s, str):
                        out[w.strip().lower()] = _normalize_accent(s)
            continue
        if isinstance(k, str) and isinstance(v, str):
            out[k.strip().lower()] = _normalize_accent(v)
    return out

def load_stress_dict() -> Dict[str, str]:
    return _sanitize(_read_json_fresh(_stress_dict_path()))

def save_stress_dict(d: Dict[str, str]) -> None:
    path = _stress_dict_path()
    path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

def clean_stress_dict() -> None:
    """Очищає файл від артефактів і нормалізує наголоси."""
    path = _stress_dict_path()
    cleaned = load_stress_dict()  # вже санітайзить + нормалізує
    path.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8")

def _preserve_case(src: str, tpl: str) -> str:
    if src.isupper():
        return tpl.upper()
    if len(src) > 1 and src[0].isupper() and src[1:].islower():
        return tpl[0].upper() + tpl[1:]
    if len(src) == 1 and src.isupper():
        return tpl.upper()
    return tpl

def apply_stress_marks(text: str) -> str:
    """
    Підставляє наголоси для відомих слів (word-boundary, IGNORECASE),
    зберігаючи регістр оригіналу.
    """
    d = load_stress_dict()
    if not d:
        return text
    # довші слова першими
    for word, stressed in sorted(d.items(), key=lambda kv: len(kv[0]), reverse=True):
        pattern = re.compile(rf"\b{re.escape(word)}\b", flags=re.IGNORECASE)
        text = pattern.sub(lambda m: _preserve_case(m.group(0), stressed), text)
    return text

def add_to_stress_dict(word: str, stressed_form: str) -> None:
    d = load_stress_dict()
    d[str(word).strip().lower()] = _normalize_accent(str(stressed_form))
    save_stress_dict(d)

def add_bulk_to_stress_dict(pairs: Iterable[tuple[str, str]]) -> None:
    d = load_stress_dict()
    for w, s in pairs:
        d[str(w).strip().lower()] = _normalize_accent(str(s))
    save_stress_dict(d)

def remove_from_stress_dict(word: str) -> bool:
    d = load_stress_dict()
    key = str(word).strip().lower()
    existed = key in d
    if existed:
        d.pop(key, None)
        save_stress_dict(d)
    return existed

def log_unknown_word(word: str) -> None:
    """
    Логує слово один раз (без дублів) і не логує, якщо слово вже є у словнику.
    Перший запис створює файл з BOM для коректного відображення у PS5.
    """
    w = str(word).strip().lower()
    if not w:
        return
    if w in load_stress_dict():
        return

    log_path = (CONFIG_ROOT / "voice" / "unknown_stress_words.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    if log_path.exists():
        text = log_path.read_text(encoding="utf-8")
        if text.startswith("\ufeff"):
            text = text[1:]
        existing = {line.strip().lower() for line in text.splitlines() if line.strip()}
        if w in existing:
            return
        with log_path.open("a", encoding="utf-8") as f:
            f.write(w + "\n")
    else:
        log_path.write_text(w + "\n", encoding="utf-8-sig")

# === Токенізація невідомих слів ===
# Слово = букви (укр/лат), опційно з внутрішніми _ або - або апострофом; без пробілів.
_WORD_RE = re.compile(r"[A-Za-zА-Яа-яІіЇїЄєҐґ]+(?:[_'\-][A-Za-zА-Яа-яІіЇїЄєҐґ]+)*")

# Базові стоп-слова (укр), щоб не засмічувати лог службовою лексикою
_STOPWORDS_UA = {
    "і","й","та","у","в","на","до","з","із","за","по",
    "що","як","це","ця","цей","ці","а","але","чи","або","не"
}

def log_unknown_words_in(text: str) -> int:
    """
    Логує всі слова з рядка, яких немає у словнику наголосів.
    Ігнорує стоп-слова та дублікати (в межах виклику).
    """
    d = load_stress_dict()
    words = _WORD_RE.findall(text or "")
    added = 0
    seen = set()
    for w in (w.lower() for w in words):
        if (not w) or (w in d) or (w in seen) or (w in _STOPWORDS_UA):
            continue
        log_unknown_word(w)
        seen.add(w)
        added += 1
    return added

def retokenize_unknown_log() -> int:
    """
    Перечитує unknown_stress_words.log, розбиває на токени за новим правилом
    і перезаписує файл у вигляді унікальних слів (без тих, що уже у словнику/стоп-словах).
    Повертає кількість рядків після перезапису.
    """
    log_path = (CONFIG_ROOT / "voice" / "unknown_stress_words.log")
    if not log_path.exists():
        return 0

    try:
        text = log_path.read_text(encoding="utf-8-sig")
    except UnicodeError:
        text = log_path.read_text(encoding="utf-8")

    tokens = [t.lower() for t in _WORD_RE.findall(text)]
    d = load_stress_dict()
    uniq, seen = [], set()
    for t in tokens:
        if (not t) or (t in d) or (t in _STOPWORDS_UA) or (t in seen):
            continue
        uniq.append(t)
        seen.add(t)

    log_path.write_text("\n".join(uniq) + ("\n" if uniq else ""), encoding="utf-8-sig")
    return len(uniq)

# === Побудова та імпорт чернетки словника наголосів ===
_VOWELS_UA = set("аеєиіїоуюяАЕЄИІЇОУЮЯ")

def _accent_last_vowel(word: str) -> str:
    """Ставить комбінований наголос на ОСТАННІЙ голосній (наївна автопідказка)."""
    s = list(word)
    for i in range(len(s) - 1, -1, -1):
        if s[i] in _VOWELS_UA:
            s[i] = s[i] + "\u0301"
            return "".join(s)
    return word

def build_stress_todo(mode: str = "last") -> Path:
    """
    Будує чернетку stress_dict.todo.json із unknown_stress_words.log.
    mode: "last" — ставить наголос на останню голосну; "none" — залишає як є.
    Повертає шлях до створеного файлу.
    """
    log_path = (CONFIG_ROOT / "voice" / "unknown_stress_words.log")
    todo_path = (CONFIG_ROOT / "voice" / "stress_dict.todo.json")
    if not log_path.exists():
        todo_path.write_text("{}\n", encoding="utf-8")
        return todo_path

    try:
        text = log_path.read_text(encoding="utf-8-sig")
    except UnicodeError:
        text = log_path.read_text(encoding="utf-8")

    words = [w.strip() for w in text.splitlines() if w.strip()]
    mapping = {}
    for w in words:
        candidate = _accent_last_vowel(w) if mode == "last" else w
        mapping[w] = candidate

    todo_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    return todo_path

def import_stress_todo(merge: bool = True) -> int:
    """
    Імпортує stress_dict.todo.json у основний словник stress_dict.json.
    merge=True — мерджить поверх існуючих; False — створює з нуля.
    Повертає кількість доданих/оновлених записів.
    """
    todo_path = (CONFIG_ROOT / "voice" / "stress_dict.todo.json")
    if not todo_path.exists():
        return 0
    todo = json.loads(todo_path.read_text(encoding="utf-8")) if todo_path.stat().st_size else {}
    if not isinstance(todo, dict):
        return 0

    cur = load_stress_dict() if merge else {}
    before = len(cur)
    for k, v in todo.items():
        if isinstance(k, str) and isinstance(v, str):
            cur[k.strip().lower()] = v
    save_stress_dict(cur)
    return len(cur) - before
