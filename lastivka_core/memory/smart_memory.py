# -*- coding: utf-8 -*-
import re

_UA_STOP = {
    "я", "ти", "він", "вона", "воно", "ми", "ви", "вони",
    "про", "і", "й", "та", "але", "або", "чи", "не", "ні", "ж", "же", "то",
    "це", "цей", "ця", "той", "такий", "таке", "така",
    "у", "в", "на", "до", "з", "із", "від", "для", "після", "перед", "без",
    "що", "як", "коли", "де", "тут", "там", "тому", "тоді", "бо"
}

_UA_ENDINGS = (
    "ями", "ами", "ові", "еві", "ах", "ях", "ів", "їв", "ей", "ій",
    "ам", "ям", "ою", "ею", "ом", "ем", "у", "ю", "і", "ї", "я", "а", "о", "е"
)

_token_re = re.compile(r"[A-Za-zА-Яа-яЇїІіЄєҐґ0-9'’]+")

def ua_stem(word: str) -> str:
    """Stem Ukrainian words, preserving proper nouns."""
    w = word.lower()
    if word and word[0].isupper():
        return w  # Return unchanged for proper nouns like "Ластівка"
    for suf in sorted(_UA_ENDINGS, key=len, reverse=True):
        if w.endswith(suf) and len(w) > len(suf) + 1:
            return w[:-len(suf)]
    return w

def extract_tokens(text: str):
    return [t for t in _token_re.findall((text or "").lower()) if t not in _UA_STOP]

def extract_topics(text: str):
    m = re.search(r"(?:про\s+(.+)|який\s+(.+)\?$)", text or "", flags=re.IGNORECASE)
    if m:
        cand = _token_re.findall((m.group(1) or m.group(2) or "").lower())
        cand = [c for c in cand if c not in _UA_STOP]
        if cand:
            return [ua_stem(cand[0])]
    toks = extract_tokens(text or "")
    for t in toks:
        s = ua_stem(t)
        if s and s not in _UA_STOP and len(s) >= 3:
            return [s]
    return []

def smart_save_interceptor(user_input: str, memory):
    if not isinstance(user_input, str):
        return None
    if not re.match(r"^\s*(запам[’'’]?ятай|запиши|пам[’'’]?ятай)\b", user_input, flags=re.IGNORECASE):
        return None
    # Skip explicit key-value pairs or "це"
    if re.search(r"[:=\-–—]|\sце\s", user_input, flags=re.IGNORECASE):
        return None
    # Auto-save free text as a thought
    m = re.search(r":\s*(.+)$", user_input)
    content = m.group(1) if m else user_input
    topics = extract_topics(content) or ["загальн"]
    for stem in topics:
        memory.add_thought(key=stem, thought=content, tone="нейтральний", tags=[stem, "auto"])
    return f"Я запамʼятала: {content}"

def smart_query_interceptor(user_input: str, memory):
    if not isinstance(user_input, str):
        return None
    if not re.match(r"^\s*(що\s+я\s+тобі\s+(говорив|казав|писав)|який\s+.+)\b", user_input, flags=re.IGNORECASE):
        return None
    topics = extract_topics(user_input)
    results, tried = [], []
    def _fetch(key):
        try:
            return memory.get_thoughts_by_key(key) or []
        except Exception:
            return []
    for stem in (topics or []):
        tried.append(stem)
        results += _fetch(stem)
    if not results:
        try:
            all_keys = list(getattr(memory, "store", {}).keys()) or []
        except Exception:
            all_keys = []
        for k in all_keys:
            if any(k.startswith(st) for st in (topics or [])):
                tried.append(k)
                results += _fetch(k)
    if not results:
        topic_txt = topics[0] if topics else "це"
        return f"Я поки нічого не зберігала про «{topic_txt}»."
    tail = results[-3:]
    lines = [f"• {r.get('text','')}" if isinstance(r, dict) else f"• {r}" for r in tail]
    return "Ти казав:\n" + "\n".join(lines)