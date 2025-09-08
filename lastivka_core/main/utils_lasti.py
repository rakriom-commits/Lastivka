# -*- coding: utf-8 -*-
# main/utils_lasti.py
import re, logging, json, tkinter as tk
from tkinter import simpledialog
from pathlib import Path
import importlib

SYSTEM_MARKERS = ("[🌀]", "[✔]", "[🔍]", "[SEC]", "[SYSTEM]")

# --- Конфіг
BASE_DIR = Path(__file__).resolve().parents[1]  # ...\lastivka_core
CONFIG_DIR = BASE_DIR / "config"
SETTINGS_PATH = CONFIG_DIR / "lastivka_settings.json"

def _load_settings():
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

SETTINGS = _load_settings()

# --- Динамічний пошук TTS-бекенду
_SPEAK = None
_SPEAKER_BACKEND = None

def _try_import(mod: str, fn: str = "speak"):
    """Пробуємо імпортувати модуль і дістати функцію speak; повертаємо (callable | None, errstr | None)."""
    try:
        m = importlib.import_module(mod)
        speak = getattr(m, fn)
        return speak, None
    except Exception as e:
        return None, f"{mod}.{fn} → {e}"

def _resolve_speaker():
    global _SPEAK, _SPEAKER_BACKEND
    if _SPEAK:
        return _SPEAK
    preferred = SETTINGS.get("tts_backend")  # напр. "speech.voice_core"
    candidates = []
    # 1) якщо вказаний tts_backend — пробуємо його ПЕРШИМ
    if isinstance(preferred, str) and preferred.strip():
        candidates.append((preferred.strip(), "speak"))
    # 2) далі — звичний порядок (ядро/диспетчер/офлайн/ін.)
    candidates += [
        ("speech.voice_core", "speak"),
        ("speech.voice_dispatcher", "speak_with_emotion"),
        ("speech.voice_module_rhvoice", "speak"),
        ("speech.voice_module", "speak"),
        ("speech.voice_module_offline", "speak"),
        ("tools.voice.balcon_speech_module", "speak"),  # останній фолбек
    ]
    errors = []
    for mod, fn in candidates:
        speak, err = _try_import(mod, fn)
        if speak:
            _SPEAK = speak
            _SPEAKER_BACKEND = mod
            logging.info(f"[TTS] Використовую бекенд: {mod}.{fn}()")
            if errors:
                logging.debug("[TTS] Попередні спроби: " + " | ".join(errors))
            return _SPEAK
        else:
            errors.append(err)
    raise ImportError("Не знайдено жодного TTS-бекенду. " + " | ".join(errors))

def get_speaker_backend() -> str:
    if _SPEAKER_BACKEND is None:
        try:
            _resolve_speaker()
        except Exception as e:
            return f"UNRESOLVED: {e}"
    return _SPEAKER_BACKEND

def _speak_with_prefs(speak_func, text, prefs: dict | None):
    """Передаємо мовні параметри, якщо бекенд їх підтримує; інакше — просто speak(text)."""
    if not prefs:
        return speak_func(str(text))
    trials = [
        {"lang": prefs.get("lang")},
        {"language": prefs.get("lang")},
        {"locale": prefs.get("locale")},
        {"voice": prefs.get("voice")},
        {"voice_code": prefs.get("voice")},
        {"voice_name": prefs.get("voice")},
        {"lang": prefs.get("lang"), "voice": prefs.get("voice")},
        {"locale": prefs.get("locale"), "voice": prefs.get("voice")},
    ]
    try:
        if hasattr(speak_func, "__self__"):
            obj = speak_func.__self__
            if hasattr(obj, "set_lang") and prefs.get("lang"):
                obj.set_lang(prefs["lang"])
            if hasattr(obj, "set_locale") and prefs.get("locale"):
                obj.set_locale(prefs["locale"])
            if hasattr(obj, "set_voice") and prefs.get("voice"):
                obj.set_voice(prefs["voice"])
    except Exception:
        pass
    for kw in trials:
        try:
            clean_kw = {k: v for k, v in kw.items() if v}
            if not clean_kw:
                continue
            return speak_func(str(text), **clean_kw)
        except TypeError:
            continue
        except Exception:
            continue
    return speak_func(str(text))

def make_sayer(tts_antispam=False, tts_prefs: dict | None = None):
    speak = _resolve_speaker()
    if not tts_antispam:
        def say_safe(text):
            try:
                if any(m in str(text) for m in SYSTEM_MARKERS):
                    logging.info(f"[SYSTEM-MSG]: {text}"); return
                _speak_with_prefs(speak, text, tts_prefs)
            except Exception as e:
                logging.exception(f"[TTS] {e}")
        return say_safe
    from time import monotonic, sleep
    _last = {"t": 0.0}
    def say_safe(text):
        if any(m in str(text) for m in SYSTEM_MARKERS):
            logging.info(f"[SYSTEM-MSG]: {text}"); return
        now = monotonic()
        dt = now - _last["t"]
        if dt < 0.12:
            sleep(0.12 - dt)
        _last["t"] = monotonic()
        try:
            _speak_with_prefs(speak, text, tts_prefs)
        except Exception as e:
            logging.exception(f"[TTS] {e}")
    return say_safe

def remove_emoji(text):
    if not isinstance(text, str): return text
    return re.sub("[" +
        "\U0001F600-\U0001F64F" + "\U0001F300-\U0001F5FF" + "\U0001F680-\U0001F6FF" +
        "\U0001F1E0-\U0001F1FF" + "\U00002700-\U000027BF" + "\U000024C2-\U0001F251" + "]+", "", text)

def make_echo(console_echo=True):
    def echo(label: str, text):
        if console_echo:
            try: print(f"{label} {remove_emoji(str(text))}")
            except Exception: print(f"{label} {text}")
    return echo

def make_input(single_tk_root=False):
    root_ref = {"root": None}
    def get_user_input():
        try:
            if single_tk_root:
                if root_ref["root"] is None:
                    root_ref["root"] = tk.Tk()
                    root_ref["root"].withdraw()
                result = simpledialog.askstring(title="Ластівка", prompt="Ти:", parent=root_ref["root"])
            else:
                root = tk.Tk()
                root.withdraw()
                result = simpledialog.askstring(title="Ластівка", prompt="Ти:")
            return result if result is not None else ""  # Повертаємо порожній рядок, якщо None
        except Exception as e:
            logging.error(f"[INPUT] Помилка в get_user_input: {e}")
            return ""  # Повертаємо порожній рядок у разі помилки
        finally:
            if not single_tk_root and 'root' in locals():
                root.destroy()  # Закриваємо вікно, якщо не single_tk_root
    return get_user_input