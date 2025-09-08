# -*- coding: utf-8 -*-
from __future__ import annotations
import re
from difflib import SequenceMatcher
from typing import List

_UA_ENDINGS = (
    "ями","ами","ові","еві","ах","ях","ів","їв","ей","ій","ам","ям",
    "ою","ею","ом","ем","у","ю","і","ї","я","а","о","е"
)
_UA_ALNUM = r"a-zA-Zа-щА-ЩЬьЮюЯяІіЇїЄєҐґ0-9"
_CLEAN_RE = re.compile(fr"[^{_UA_ALNUM}\s']+", re.UNICODE)

def ua_stem(w: str) -> str:
    w = (w or "").lower().replace("’", "'").strip()
    for suf in sorted(_UA_ENDINGS, key=len, reverse=True):
        if w.endswith(suf) and len(w) > len(suf) + 1:
            return w[:-len(suf)]
    return w

def normalize_key(s: str) -> str:
    s = (s or "").strip().lower().replace("’", "'")
    s = re.sub(r"\s+", " ", s)
    return ua_stem(s)

def normalize_text(text: str) -> str:
    return _CLEAN_RE.sub(" ", (text or "").lower()).strip()

def tokenize(text: str) -> List[str]:
    return [t for t in normalize_text(text).split() if t and len(t) > 1]

def stem_token(tok: str) -> str:
    return ua_stem(tok or "")

def fuzzy_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

def lev1(a: str, b: str) -> bool:
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diff = sum(x != y for x, y in zip(a, b))
        if diff <= 1: return True
        if diff == 2:
            for i in range(len(a) - 1):
                if a[i] != b[i] and a[i+1] != b[i+1]:
                    if a[:i] + a[i+1] + a[i] + a[i+2:] == b:
                        return True
        return False
    if len(a) < len(b): a, b = b, a
    i = j = d = 0
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            i += 1; j += 1
        else:
            d += 1; i += 1
            if d > 1: return False
    if i < len(a): d += len(a) - i
    return d <= 1
