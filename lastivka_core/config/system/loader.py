# -*- coding: utf-8 -*-
# lastivka_core/config/system/loader.py

from __future__ import annotations
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Union

# YAML (опційно)
try:
    import yaml  # pip install pyyaml
except Exception:
    yaml = None


def _config_root() -> Path:
    """
    Визначає корінь конфігів:
    - LASTIVKA_CONFIG_ROOT (ENV) має пріоритет;
    - інакше, якщо файл лежить у config/system → root = config.
    """
    env = os.environ.get("LASTIVKA_CONFIG_ROOT")
    if env:
        return Path(env).resolve()

    here = Path(__file__).resolve()
    # .../config/system/loader.py → .../config
    if here.parent.name == "system":
        return here.parent.parent.resolve()
    # fallback: якщо файл покладуть прямо в config/
    return here.parent.resolve()


CONFIG_ROOT: Path = _config_root()


def _resolve(name: Union[str, Path]) -> Path:
    """
    Повертає абсолютний шлях до файлу конфігу.
    Підтримує як 'voice/voice_config.json', так і просто 'voice_config.json'.
    Якщо прямого шляху нема — здійснює пошук по всьому дереву CONFIG_ROOT.
    """
    p = (CONFIG_ROOT / str(name)).resolve()
    if p.exists():
        return p

    target = Path(name).name
    for cand in CONFIG_ROOT.rglob(target):
        if cand.is_file():
            return cand.resolve()

    raise FileNotFoundError(f"Config not found: {name} (root={CONFIG_ROOT})")


# ---- Кешовані базові лоадери (без default-параметрів) ----------------------

@lru_cache(maxsize=256)
def load_text(name: Union[str, Path], encoding: str = "utf-8") -> str:
    return _resolve(name).read_text(encoding=encoding)

@lru_cache(maxsize=256)
def _load_json_cached(name: Union[str, Path]) -> Any:
    return json.loads(load_text(name))


def load_json(name: Union[str, Path],
              default: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    JSON-лоадер з підтримкою default.
    ВАЖЛИВО: кеш — лише для варіанту без default (через _load_json_cached),
    щоб уникнути помилки "unhashable type: 'dict'".
    """
    try:
        return _load_json_cached(name)
    except FileNotFoundError:
        return {} if default is None else default


@lru_cache(maxsize=256)
def load_yaml(name: Union[str, Path]) -> Any:
    if yaml is None:
        raise RuntimeError("PyYAML не встановлено (pip install pyyaml)")
    return yaml.safe_load(load_text(name))


def exists(name: Union[str, Path]) -> bool:
    try:
        _resolve(name)
        return True
    except FileNotFoundError:
        return False


# ---- Агрегатор дефолтних налаштувань ---------------------------------------

def get_config() -> Dict[str, Any]:
    """
    Базовий агрегат системних налаштувань з дефолтами та підвантаженням підрозділів.
    """
    base: Dict[str, Any] = {
        "env": os.getenv("LASTIV_ENV", "dev"),
        "security": {"slow_timeout_ms": 300},
    }

    # Білий список користувачів/токенів
    base["whitelist"] = load_json(
        "system/whitelist.json",
        {"users": ["Олег", "Софія"], "tokens": []},
    )

    # Додаткові системні налаштування (необов'язково)
    settings = load_json("system/lastivka_settings.json", {})
    if settings:
        base["settings"] = settings

    # Конфіги голосу
    base["voice"] = {
        "config":  load_json("voice/voice_config.json", {}),
        "accents": load_json("voice/accents.json", {}),
        "stress":  load_json("voice/stress_dict.json", {}),
        "emotion": load_json("voice/emotion_config.json", {}),
    }

    # Перекриття через YAML (опційно)
    if exists("system/config.yaml"):
        override = load_yaml("system/config.yaml") or {}
        # просте поверхневе злиття; за потреби зробимо deep-merge
        return {**base, **override}

    return base
