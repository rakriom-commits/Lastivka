# -*- coding: utf-8 -*-
from __future__ import annotations
import os
from typing import Set

try:
    import yaml  # pyyaml
except Exception:
    yaml = None

_CACHE: Set[str] = set()
_LOADED = False
_PATHS = [
    os.path.join("lastivka_core", "config", "trusts.yaml"),
    os.path.join("config", "trusts.yaml"),
]

def _load_once() -> None:
    global _LOADED, _CACHE
    if _LOADED:
        return
    for p in _PATHS:
        if os.path.exists(p) and yaml is not None:
            with open(p, "r", encoding="utf-8-sig") as fh:
                data = yaml.safe_load(fh) or {}
                _CACHE = set(data.get("trusted_identities", []) or [])
                _LOADED = True
                return
    _LOADED = True

def is_trusted(identity: str | None) -> bool:
    _load_once()
    return bool(identity) and identity in _CACHE
