# -*- coding: utf-8 -*-
"""
manager.py — оновлений (2025-08-20)

- Узгоджено з index.py (normalize, export_all).
- Повернено alias normalize_text = normalize для сумісності.
- Додано метод export_all() як офіційний API.
- Рідна підтримка tags у записах.
- Прибрано усі циклічні імпорти (ніяких from .manager import ...).
- CLI внизу файлу використовує глобальний MEMORY.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .index import MemoryIndex, normalize, normalize_key, tokenize, fuzzy

# alias для сумісності
normalize_text = normalize
lev1 = lambda a, b: fuzzy(a, b) > 0.8
_lev1 = lev1  # для старих тестів

# === Константи ===
ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILE = Path(os.getenv("LASTIVKA_MEMORY_CONFIG", ROOT / "config" / "memory_store.json"))

DEFAULT_STORE_SKELETON: Dict[str, Any] = {"triggers": {}}

# === Допоміжні IO-функції ===
def _ensure_files() -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(
            json.dumps(DEFAULT_STORE_SKELETON, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

def _safe_write(path: Path, data: dict) -> None:
    tmp_fd, tmp_path = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

def _read_json(path: Path) -> Dict[str, Any]:
    try:
        if not path.exists():
            return {}
        txt = path.read_text(encoding="utf-8-sig")
        if not txt.strip():
            return {}
        data = json.loads(txt)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}

# === Клас пам'яті ===
class MemoryManager:
    def __init__(self) -> None:
        self.memory: Dict[str, List[Dict[str, Any]]] = {}
        self.triggers: Dict[str, Dict[str, Any]] = {}
        self._index: Optional[MemoryIndex] = None
        self._dirty: bool = True
        _ensure_files()
        self.load_memory()

    # --- Службове ---
    def _maybe_build(self) -> None:
        if self._index is None or self._dirty:
            self._index = MemoryIndex(self.memory)
            self._index.build()
            self._dirty = False

    def _augment_query(self, q: str) -> str:
        toks = tokenize(normalize(q))
        stems = [normalize_key(t) for t in toks if normalize_key(t) and normalize_key(t) != t]
        return (q or "").strip() + (" " + " ".join(stems) if stems else "")

    # --- IO ---
    def load_memory(self) -> None:
        raw = _read_json(CONFIG_FILE) or {}
        self.triggers = raw.get("triggers", {}) or {}
        self.memory = {k: v for k, v in raw.items() if k != "triggers" and isinstance(v, list)}
        self._dirty = True

    def _dump(self) -> dict:
        data = dict(self.memory)
        if self.triggers:
            data["triggers"] = self.triggers
        return data

    def save_memory(self) -> None:
        _safe_write(CONFIG_FILE, self._dump())

    # --- CRUD ---
    def add_thought(
        self,
        key: str,
        thought: str,
        tone: str = "нейтральний",
        tags: Optional[List[str]] = None,
        *,
        triple: Optional[Tuple[Any, Any, Any]] = None,
        rel: Optional[str] = None,
    ) -> None:
        key_raw = (key or "").strip()
        if not key_raw:
            return
        key_norm = normalize_key(key_raw)

        self.memory.setdefault(key_norm, [])
        t_norm = (thought or "").strip().lower()

        for e in self.memory[key_norm]:
            if e.get("text", "").strip().lower() == t_norm and e.get("tone") == tone:
                return

        rec = {
            "key_raw": key_raw,
            "key_norm": key_norm,
            "text": (thought or "").strip(),
            "tone": tone,
            "timestamp": datetime.now().isoformat(),
            "tags": [str(t).strip().lower() for t in (tags or []) if str(t).strip()],
            "rel": rel,
            "triple": triple if triple else (key_norm, rel or "is", (thought or "").strip()),
        }
        self.memory[key_norm].append(rec)
        self._dirty = True
        self.save_memory()

    def get_thoughts_by_key(self, k: str) -> List[Dict[str, Any]]:
        return list(self.memory.get(normalize_key(k), []))

    def get_all_memory(self) -> Dict[str, List[Dict[str, Any]]]:
        return dict(self.memory)

    def delete_thoughts_by_key(self, k: str) -> None:
        k = normalize_key(k)
        if k in self.memory:
            del self.memory[k]
            self._dirty = True
            self.save_memory()

    def clear_memory(self) -> None:
        self.memory = {}
        self._dirty = True
        self.save_memory()

    def export_memory(self, path: str | Path) -> None:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        _safe_write(out, self._dump())

    def export_all(self) -> Dict[str, List[Dict[str, Any]]]:
        """Офіційний API для index.py"""
        return self.get_all_memory()

    # --- Додаткові ---
    def get_all_keys(self) -> List[str]:
        return sorted(self.memory.keys())

    def search_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        t = (tag or "").strip().lower()
        out: List[Dict[str, Any]] = []
        for arr in self.memory.values():
            for rec in arr:
                if t in [str(x).lower() for x in (rec.get("tags") or [])]:
                    out.append(rec)
        return out

    # --- Пошук ---
    def find_thoughts(self, qtext: str) -> List[Dict[str, Any]]:
        q = normalize_key(qtext)
        out: List[Dict[str, Any]] = []
        out.extend(self.memory.get(q, []))
        if out:
            return out

        for k, arr in self.memory.items():
            if k.startswith(q):
                out.extend(arr)
        if out:
            return out

        qlen = len(q)
        for k in (k for k in self.memory.keys() if abs(len(k) - qlen) <= 2):
            if lev1(k, q):
                out.extend(self.memory.get(k, []))
        return out

    def smart_search(
        self,
        query: str,
        limit: int = 10,
        weights: Optional[Dict[str, float]] = None,
        debug: bool = False,
    ) -> List[Dict[str, Any]]:
        self._maybe_build()
        assert self._index is not None
        aug_query = self._augment_query(query)
        ranked = self._index.search(aug_query, weights=weights, limit=limit, debug=debug)
        out: List[Dict[str, Any]] = []
        for key_norm, rec, score in ranked:
            item = {"key": key_norm, "score": round(float(score), 4)}
            item.update(rec)
            out.append(item)
        return out

    def ask(self, query: str) -> Optional[Dict[str, Any]]:
        top = (self.smart_search(query, limit=1) or [])
        if top:
            return top[0]

        qn = normalize(query)
        if re.search(r"\b(куп\w*|придб\w*|візьми|додай до списку)\b", qn):
            tag_priority = {"покупка": 3, "покупки": 3, "товар": 3, "магазин": 3, "напій": 2, "їжа": 1}
            best, best_score, best_key = None, (-1, ""), None
            for k, arr in self.memory.items():
                for rec in arr:
                    tags = [str(t).lower() for t in (rec.get("tags") or [])]
                    pr = max((tag_priority.get(t, 0) for t in tags), default=0)
                    ts = rec.get("timestamp") or ""
                    score = (pr, ts)
                    if score > best_score:
                        best_score, best, best_key = score, rec, k
            if best:
                return {
                    "key": best_key,
                    "score": 50.0,
                    "key_raw": best.get("key_raw", best_key),
                    "key_norm": best_key,
                    "text": best.get("key_raw", best_key),
                    "tone": best.get("tone"),
                    "timestamp": best.get("timestamp"),
                    "tags": best.get("tags"),
                    "rel": best.get("rel"),
                    "triple": best.get("triple"),
                }
        return None

# === Глобальний екземпляр ===
MEMORY = MemoryManager()
memory = MEMORY

# === CLI (для зручності локального виклику) ===
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Управління пам’яттю Ластівки")
    p.add_argument('--search', type=str)
    p.add_argument('--key', type=str)
    p.add_argument('--delete', type=str)
    p.add_argument('--export', type=str)
    p.add_argument('--find', type=str)
    p.add_argument('--smart', type=str)
    p.add_argument('--ask', type=str)
    p.add_argument('--weights', type=str)
    p.add_argument('--debug', action='store_true')
    p.add_argument('--test', action='store_true')
    p.add_argument('--add', nargs=2, metavar=('KEY', 'TEXT'))
    p.add_argument('--tone', type=str, default='нейтральний')
    p.add_argument('--tags', type=str)
    p.add_argument('--rel', type=str, default=None)
    p.add_argument('--clear', action='store_true')
    p.add_argument('--keys', action='store_true')
    p.add_argument('--stats', action='store_true')

    args = p.parse_args()

    if args.add:
        key, text = args.add
        tags = [t.strip() for t in (args.tags.split(',') if args.tags else []) if t.strip()]
        MEMORY.add_thought(key, text, tone=args.tone, tags=tags, rel=args.rel)
        print(f"[+] Додано: {key!r} → {text!r}")
    elif args.search:
        print(json.dumps(MEMORY.smart_search(args.search, debug=args.debug), ensure_ascii=False, indent=2))
    elif args.key:
        print(json.dumps(MEMORY.get_thoughts_by_key(args.key), ensure_ascii=False, indent=2))
    elif args.delete:
        MEMORY.delete_thoughts_by_key(args.delete)
        print(f"[✓] Видалено '{args.delete}'")
    elif args.export:
        MEMORY.export_memory(args.export)
        print(f"[⇳] Експортовано: {args.export}")
    elif args.find:
        print(json.dumps(MEMORY.find_thoughts(args.find), ensure_ascii=False, indent=2))
    elif args.smart:
        weights = None
        if args.weights:
            try:
                weights = json.loads(args.weights)
            except Exception:
                pass
        print(json.dumps(MEMORY.smart_search(args.smart, weights=weights, debug=args.debug), ensure_ascii=False, indent=2))
    elif args.ask:
        ans = MEMORY.ask(args.ask)
        print(json.dumps({"answer": None} if not ans else {
            "answer": ans.get("text"),
            "key": ans.get("key"),
            "score": ans.get("score"),
            "timestamp": ans.get("timestamp"),
        }, ensure_ascii=False, indent=2))
    elif args.clear:
        MEMORY.clear_memory()
        print("[∅] Пам’ять очищено")
    elif args.keys:
        print(json.dumps(MEMORY.get_all_keys(), ensure_ascii=False, indent=2))
    elif args.stats:
        total_records = sum(len(v) for v in MEMORY.memory.values())
        print(json.dumps({
            "keys": len(MEMORY.memory),
            "records": total_records,
            "triggers": len(MEMORY.triggers or {}),
            "config_file": str(CONFIG_FILE),
        }, ensure_ascii=False, indent=2))
    elif args.test:
        MEMORY.clear_memory()
        MEMORY.add_thought("кава", "чорна", rel="is", tags=["напій", "покупка"])
        print("--smart 'купити кави'--")
        print(json.dumps(MEMORY.smart_search("купити кави", limit=5, debug=True), ensure_ascii=False, indent=2))
        print("--ask 'що я тобі казав купити?'--")
        print(json.dumps(MEMORY.ask("що я тобі казав купити?") or {"answer": None}, ensure_ascii=False, indent=2))
    else:
        print("[ℹ] Використай --add, --search, --key, --delete, --export, --find, --smart, --ask, --clear, --keys, --stats або --test")
