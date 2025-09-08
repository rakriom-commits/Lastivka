# speech/voice_dispatcher.py — офлайн-first, керування через env, сумісний зі старим API
import importlib, logging, os, shutil, socket
from typing import List, Tuple, Optional, Callable

# Емоції можна вимкнути через LASTIVKA_DISABLE_EMOTION=1
USE_EMOTION = os.getenv("LASTIVKA_DISABLE_EMOTION") != "1"
if USE_EMOTION:
    try:
        from speech.emotion_reactor import get_emotion_reaction
    except Exception:
        USE_EMOTION = False

log = logging.getLogger("voice_dispatcher")

LANG_PREFS = {"lang": "uk", "locale": "uk-UA", "voice": None}
LANG_LOCK = True

def _try_import(mod: str, fn: str = "speak"):
    try:
        m = importlib.import_module(mod)
        f = getattr(m, fn)
        return m, f, None
    except Exception as e:
        return None, None, f"{mod}.{fn}: {e}"

def _set_lang_hints(module, prefs):
    if not module: return
    try:
        if hasattr(module, "set_lang") and prefs.get("lang"):     module.set_lang(prefs["lang"])
        if hasattr(module, "set_locale") and prefs.get("locale"): module.set_locale(prefs["locale"])
        if hasattr(module, "set_voice") and prefs.get("voice"):   module.set_voice(prefs["voice"])
    except Exception:
        pass
    for name, val in {
        "LANG": prefs.get("lang"), "LANGUAGE": prefs.get("lang"), "TTS_LANG": prefs.get("lang"),
        "LOCALE": prefs.get("locale"), "TTS_LOCALE": prefs.get("locale"),
        "VOICE": prefs.get("voice"), "VOICE_NAME": prefs.get("voice"), "TTS_VOICE": prefs.get("voice"),
    }.items():
        try:
            if val is not None and hasattr(module, name):
                setattr(module, name, val)
        except Exception:
            continue

def _internet_ok(timeout: float = 2.0) -> bool:
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        return True
    except Exception:
        return False

def _rhvoice_available() -> bool:
    return bool(shutil.which("rhvoice") or shutil.which("rhvoice-play"))

def _normalize_name(mod: str) -> str:
    mod = (mod or "").strip()
    if not mod: return ""
    if mod.startswith("speech."): return mod
    if mod.startswith("lastivka_core.speech."):
        return mod.replace("lastivka_core.", "", 1)  # у проекті імпортуємо як "speech.xxx"
    return mod

def _desired_order() -> List[Tuple[str, str]]:
    """
    Порядок:
    1) LASTIVKA_VOICE_ORDER (через кому), напр.:
       speech.voice_module_fast,speech.voice_module_offline,speech.voice_module
    2) За замовчуванням — офлайн-first:
       fast → (rhvoice?) → offline → (online якщо не вимкнено і є інтернет)
    """
    env_order = (os.getenv("LASTIVKA_VOICE_ORDER") or "").strip()
    items: List[str] = []
    if env_order:
        items = [_normalize_name(x) for x in env_order.split(",") if _normalize_name(x)]
    else:
        items = ["speech.voice_module_fast"]
        if _rhvoice_available():
            items.append("speech.voice_module_rhvoice")
        items.append("speech.voice_module_offline")
        if os.getenv("LASTIVKA_TTS_DISABLE_ONLINE") != "1" and _internet_ok():
            items.append("speech.voice_module")  # online лише в кінці

    # Якщо явно заборонено онлайн — приберемо навіть якщо він у env
    if os.getenv("LASTIVKA_TTS_DISABLE_ONLINE") == "1":
        items = [m for m in items if m != "speech.voice_module"]

    return [(m, "speak") for m in items]

_RESOLVED: List[Tuple[object, Callable, str]] = []
_NOT_AVAILABLE = set()

def _resolve_all() -> List[Tuple[object, Callable, str]]:
    global _RESOLVED
    if _RESOLVED:
        return _RESOLVED
    order = _desired_order()
    errors = []
    resolved = []
    for modname, fn in order:
        if modname in _NOT_AVAILABLE:
            continue
        mod, speak, err = _try_import(modname, fn)
        if mod and speak:
            ok = True
            try:
                is_ready = getattr(mod, "is_ready", None)
                if callable(is_ready):
                    ok = bool(is_ready())
            except Exception:
                ok = True
            if ok:
                _set_lang_hints(mod, LANG_PREFS)
                resolved.append((mod, speak, modname))
                continue
        _NOT_AVAILABLE.add(modname)
        errors.append(err)
    if not resolved:
        raise ImportError("voice_dispatcher: no modules resolved: " + " | ".join([e for e in errors if e]))
    _RESOLVED = resolved
    try:
        log.info("[voice_dispatcher] resolved order: " + " → ".join(m for *_, m in _RESOLVED))
    except Exception:
        print("[voice_dispatcher] resolved order: " + " → ".join(m for *_, m in _RESOLVED))
    return _RESOLVED

def _speak_with_prefs(speak_fn: Callable, mod, text, prefs):
    if LANG_LOCK:
        _set_lang_hints(mod, prefs)
    trials = [
        {"lang": prefs.get("lang")}, {"language": prefs.get("lang")},
        {"locale": prefs.get("locale")},
        {"voice": prefs.get("voice")}, {"voice_name": prefs.get("voice")}, {"voice_code": prefs.get("voice")},
        {"lang": prefs.get("lang"), "voice": prefs.get("voice")},
        {"locale": prefs.get("locale"), "voice": prefs.get("voice")},
    ]
    for kw in trials:
        try:
            clean = {k: v for k, v in kw.items() if v}
            if not clean: continue
            return speak_fn(str(text), **clean)
        except TypeError:
            continue
        except Exception:
            continue
    return speak_fn(str(text))

def speak_with_emotion(text: str):
    """Старий API. Якщо емоції вимкнені — читаємо як є, без затримок."""
    payload = str(text)
    if USE_EMOTION:
        try:
            payload = get_emotion_reaction(text)["reaction"]
        except Exception:
            payload = str(text)
    resolved = _resolve_all()
    last_err = None
    for mod, speak_fn, modname in resolved:
        try:
            logging.debug(f"[voice_dispatcher] try {modname}")
            return _speak_with_prefs(speak_fn, mod, payload, LANG_PREFS)
        except Exception as e:
            last_err = e
            logging.warning(f"[voice_dispatcher] {modname} failed: {e}. Falling over to next…")
            continue
    logging.error(f"[voice_dispatcher] all backends failed: {last_err}")
    return None

def speak(text: str, lang: Optional[str] = None, **kwargs):
    """Додатковий універсальний API (без емоцій)."""
    resolved = _resolve_all()
    prefs = dict(LANG_PREFS)
    if lang: prefs["lang"] = lang
    last_err = None
    for mod, speak_fn, modname in resolved:
        try:
            logging.debug(f"[voice_dispatcher] try {modname}")
            return _speak_with_prefs(speak_fn, mod, text, prefs)
        except Exception as e:
            last_err = e
            logging.warning(f"[voice_dispatcher] {modname} failed: {e}. Falling over to next…")
            continue
    logging.error(f"[voice_dispatcher] all backends failed: {last_err}")
    return None

if __name__ == "__main__":
    speak_with_emotion("Перевірка української озвучки (офлайн-first).")
