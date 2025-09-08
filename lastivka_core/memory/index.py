# -*- coding: utf-8 -*-
from __future__ import annotations
import re
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Optional

# ===== Нормалізація / токенізація =====
UA_ALNUM = r"a-zA-Zа-щА-ЩЬьЮюЯяІіЇїЄєҐґ0-9"
CLEAN_RE = re.compile(fr"[^{UA_ALNUM}\s']+", re.UNICODE)
_UA_ENDINGS = (
    "ями", "ами", "ові", "еві", "ах", "ях", "ів", "іїв", "ей", "ій", "ам", "ям",
    "ою", "ею", "ом", "ем", "у", "ю", "і", "ї", "я", "а", "о", "е"
)

def _ua_stem(w: str) -> str:
    """Stem Ukrainian words, preserving proper nouns."""
    w = (w or "").lower().replace("’", "'").strip()
    # Preserve proper nouns (starting with a capital letter in original)
    if w and w[0].isupper():
        return w
    for suf in sorted(_UA_ENDINGS, key=len, reverse=True):
        if w.endswith(suf) and len(w) > len(suf) + 1:
            return w[:-len(suf)]
    return w

def normalize(text: str) -> str:
    return CLEAN_RE.sub(" ", (text or "").lower()).strip()

def normalize_key(s: str) -> str:
    s = (s or "").strip().lower().replace("’", "'")
    s = re.sub(r"\s+", " ", s)
    # Preserve proper nouns
    if s and s[0].isupper():
        return s
    return _ua_stem(s)

def tokenize(text: str) -> List[str]:
    return [t for t in normalize(text).split() if t and len(t) > 1]

def stem_token(tok: str) -> str:
    return _ua_stem(tok or "")

def fuzzy(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

# ===== Допоміжне: нормалізація та мердж формату пам'яті =====
def _normalize_memory_dict(raw: dict) -> Dict[str, List[dict]]:
    """
    Привести будь-який сирий формат до dict[str] -> list[dict]
    Підтримує: list, dict (одиночний запис), dict із 'items' або 'entries'.
    Ігнорує некоректні типи.
    """
    out: Dict[str, List[dict]] = {}
    if not isinstance(raw, dict):
        return out
    for k, v in raw.items():
        bucket: List[dict] = []
        if isinstance(v, list):
            bucket = [x for x in v if isinstance(x, dict)]
        elif isinstance(v, dict):
            if "items" in v and isinstance(v["items"], list):
                bucket = [x for x in v["items"] if isinstance(x, dict)]
            elif "entries" in v and isinstance(v["entries"], list):
                bucket = [x for x in v["entries"] if isinstance(x, dict)]
            else:
                bucket = [v]
        if bucket:
            out[str(k)] = bucket
    return out

def _merge_mem_dicts(a: dict, b: dict) -> dict:
    """
    Об'єднати два словники пам'яті формату dict[str] -> list[dict] з
    простим дедупом за ('text' або 'value', 'tone').
    """
    out: Dict[str, List[dict]] = {}
    for src in (a or {}), (b or {}):
        for k, arr in src.items():
            if not isinstance(arr, list):
                continue
            bucket = out.setdefault(k, [])
            seen = {
                (
                    (x.get("text") or x.get("value") or "").strip().lower(),
                    (x.get("tone") or "").strip().lower()
                )
                for x in bucket if isinstance(x, dict)
            }
            for rec in arr:
                if not isinstance(rec, dict):
                    continue
                sig = (
                    (rec.get("text") or rec.get("value") or "").strip().lower(),
                    (rec.get("tone") or "").strip().lower()
                )
                if sig not in seen:
                    bucket.append(rec)
                    seen.add(sig)
    return out

# ===== Індекс =====
class MemoryIndex:
    def __init__(self, memory: Optional[Dict[str, List[dict]]] = None) -> None:
        self.memory: Dict[str, List[dict]] = memory or {}
        self.inv: Dict[str, List[Tuple[str, int]]] = {}
        self._build()

    def _build(self) -> None:
        self.inv.clear()
        for k, thoughts in self.memory.items():
            if not isinstance(thoughts, list):
                continue
            # токени + стеми з ключа
            k_tokens = set(tokenize(k))
            k_tokens |= {stem_token(t) for t in k_tokens}
            for i, t in enumerate(thoughts):
                if not isinstance(t, dict):
                    continue
                tokens: set[str] = set()
                # текст запису (підтримуємо 'text' і 'value')
                text = t.get("text", "") or t.get("value", "") or ""
                tokens |= set(tokenize(text))
                # triple.obj → індексуємо
                tri = t.get("triple")
                if tri and isinstance(tri, (list, tuple)) and len(tri) == 3:
                    obj = tri[2] or ""
                    tokens |= set(tokenize(obj))
                # додати стеми та токени ключа
                tokens |= {stem_token(tt) for tt in tokens}
                tokens |= k_tokens
                for tok in tokens:
                    if tok:
                        self.inv.setdefault(tok, []).append((k, i))

    def build(self) -> None:
        self._build()

    def search(
        self,
        query: str,
        limit: int = 10,
        weights: Optional[dict] = None,
        debug: bool = False
    ) -> List[Tuple[str, dict, float]]:
        q_text = normalize(query)
        q_key = normalize_key(q_text)
        q_tokens_text = set(tokenize(q_text))
        q_tokens_key = set(tokenize(q_key))
        q_tokens = q_tokens_text | q_tokens_key
        q_stems = {stem_token(t) for t in q_tokens}
        if debug:
            print(f"[DEBUG] Q_TEXT='{q_text}' Q_KEY='{q_key}'")
            print(f"[DEBUG] Q_TOKENS(text)={sorted(q_tokens_text)} "
                  f"Q_TOKENS(key)={sorted(q_tokens_key)} "
                  f"Q_STEMS={sorted(q_stems)}")
        if not q_tokens:
            return []
        candidates: Dict[Tuple[str, int], float] = {}
        # Ваги ранжування
        W = {
            "exact": 100.0,
            "prefix": 65.0,
            "fuzzy": 55.0,
            "token": 20.0,
            "text_match": 25.0,
            "prefix_token": 5.0,
            "text_fuzzy": 30.0,
            "triple_obj": 40.0,
            "stem_bonus": 5.0,
            "key_token": 60.0,
        }
        if isinstance(weights, dict):
            W.update(weights)
        # 0) збіг токенів/стемів КЛЮЧА з токенами запиту
        for key, thoughts in self.memory.items():
            k_tokens = set(tokenize(key))
            k_stems = {stem_token(t) for t in k_tokens} | {stem_token(key)}
            if (k_tokens & q_tokens) or (k_stems & q_stems) or (key in q_tokens):
                for i in range(len(thoughts)):
                    candidates[(key, i)] = max(candidates.get((key, i), 0.0), W["key_token"])
        # 1) матчі по ключу
        for key, thoughts in self.memory.items():
            key_n = normalize_key(key)
            if key_n == q_key:
                base = W["exact"]
            elif key_n.startswith(q_key):
                base = W["prefix"]
            else:
                base = W["fuzzy"] * fuzzy(key_n[:64], q_key[:64])
            if base >= 20.0:
                for i in range(len(thoughts)):
                    candidates[(key, i)] = max(candidates.get((key, i), 0.0), base)
        # 2) лексичний індекс (токени + стеми)
        hits: List[Tuple[str, int]] = []
        for tok in q_tokens:
            hits.extend(self.inv.get(tok, []))
        for st in q_stems:
            hits.extend(self.inv.get(st, []))
        for key, i in hits:
            t = self.memory[key][i]
            text = t.get("text", "") or t.get("value", "") or ""
            text_n = normalize(text)
            text_tokens = set(tokenize(text_n))
            text_stems = {stem_token(w) for w in text_tokens}
            score = W["token"] * len(text_tokens & q_tokens)
            if q_text in text_n:
                score += W["text_match"]
            for qt in q_tokens:
                if any(w.startswith(qt) for w in text_tokens):
                    score += W["prefix_token"]
            if text_stems & q_stems:
                score += W["stem_bonus"]
            score += W["text_fuzzy"] * fuzzy(text_n[:256], q_text[:256])
            tri = t.get("triple")
            if tri and isinstance(tri, (list, tuple)) and len(tri) == 3:
                obj = tri[2] or ""
                obj_n = normalize(obj)
                obj_tokens = set(tokenize(obj_n))
                obj_stems = {stem_token(w) for w in obj_tokens}
                if q_text in obj_n:
                    score += W["triple_obj"]
                score += W["token"] * len(obj_tokens & q_tokens)
                if obj_stems & q_stems:
                    score += W["stem_bonus"]
            prev = candidates.get((key, i), 0.0)
            if score > prev:
                candidates[(key, i)] = score
        # 3) fallback: частковий збіг ключів
        if not candidates:
            for key, thoughts in self.memory.items():
                k = normalize_key(key)
                if any(k.startswith(t) or t.startswith(k) for t in q_tokens | q_stems):
                    for i in range(len(thoughts)):
                        candidates[(key, i)] = max(candidates.get((key, i), 0.0), 35.0)
        ranked = sorted(candidates.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        out: List[Tuple[str, dict, float]] = []
        for (key, i), sc in ranked:
            out.append((key, self.memory[key][i], sc))
        if debug:
            dbg = [round(sc, 2) for (_, _), sc in ranked]
            print(f"[DEBUG] index.search('{query}') -> {len(out)}: {dbg}")
        return out

# ====== PUBLIC WRAPPERS for CLI (rebuild/verify/compact) ======
_LAST_INDEX: Optional[MemoryIndex] = None

def _get_api():
    """Підхопити високорівневий менеджер пам'яті, якщо є."""
    try:
        from .manager import MemoryManager
        return MemoryManager()
    except Exception:
        return None

# --- Фолбек: напряму з long_term.long_memory ---
try:
    from .long_term.long_memory import list_memories as _lt_list_memories
except Exception:
    _lt_list_memories = None

def _try_manager_dump(api) -> Tuple[Dict[str, List[dict]], str]:
    # 1) Прямий експорт із менеджера
    for name in ("export_all", "get_all_memory", "dump", "snapshot", "list_memories", "all"):
        fn = getattr(api, name, None)
        if callable(fn):
            try:
                data = fn()
                nm = _normalize_memory_dict(data)
                if nm:
                    return nm, f"manager.{name}"
            except Exception:
                pass
    # 2) Спроба зібрати з частин (short/long)
    try:
        d: Dict[str, List[dict]] = {}
        for part in ("short", "long", "short_term", "long_term"):
            fn = getattr(api, f"export_{part}", None)
            if callable(fn):
                sub = fn()
                nm = _normalize_memory_dict(sub)
                for k, v in nm.items():
                    d.setdefault(k, []).extend(v)
        if d:
            return d, "manager.parts"
    except Exception:
        pass
    return {}, "manager.none"

def _load_memory_dict() -> Tuple[Dict[str, List[dict]], str]:
    """
    Повертає (нормалізована_пам'ять, label_джерела).
    МЕРДЖИТЬ manager.* і long_memory, якщо доступні обидва.
    """
    # 1) manager.*
    mgr_nm, mgr_src = {}, "manager.none"
    api = _get_api()
    if api:
        mgr_nm, mgr_src = _try_manager_dump(api)
    # 2) long_memory
    lm_nm, lm_src = {}, "long_memory.none"
    if _lt_list_memories:
        try:
            data = _lt_list_memories()
            lm_nm = _normalize_memory_dict(data)
            if lm_nm:
                lm_src = "long_memory"
        except Exception:
            pass
    # 3) МЕРДЖ і маркування джерела
    if mgr_nm and lm_nm:
        merged = _merge_mem_dicts(mgr_nm, lm_nm)
        return merged, f"{mgr_src}+{lm_src}"
    if mgr_nm:
        return mgr_nm, mgr_src
    if lm_nm:
        return lm_nm, lm_src
    return {}, "empty"

def rebuild() -> bool:
    """Перебудова індексу з актуальної пам'яті + діагностика джерела."""
    global _LAST_INDEX
    memory, source = _load_memory_dict()
    _LAST_INDEX = MemoryIndex(memory)
    try:
        keys = len(memory)
        entries = sum(len(v) for v in memory.values())
        toks = len(_LAST_INDEX.inv)
        print(f"[INDEX] rebuild: source={source}, keys={keys}, entries={entries}, tokens={toks}")
    except Exception:
        print(f"[INDEX] rebuild: source={source}, OK")
    return True

def verify() -> bool:
    """Легка перевірка індексу."""
    global _LAST_INDEX
    if _LAST_INDEX is None:
        rebuild()
    try:
        toks = len(_LAST_INDEX.inv)
        _ = _LAST_INDEX.search("перевірка", limit=1)
        print(f"[INDEX] verify: tokens={toks}, probe=OK")
    except Exception as e:
        print(f"[INDEX] verify: WARN → {e}")
        return False
    return True

def compact() -> bool:
    """Поки що no-op (індекс у пам'яті)."""
    print("[INDEX] compact: nothing to compact (noop)")
    return True