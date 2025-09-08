# offline_tts.py — RHVoice/SAPI wrapper (lazy log, thread + process safe)
# Лог "[OfflineTTS pid=...] voice → ..." з’являється лише:
#   • один раз при ПЕРШОМУ speak() за сесію
#   • ще раз лише при РЕАЛЬНІЙ зміні голосу (set_voice)

from __future__ import annotations
import os
import atexit
import threading
import builtins
import sys
import time
import pythoncom
try:
    from win32com.client import Dispatch
    import win32event, win32api, win32con
except Exception as e:  # PyWin32 має бути встановлено
    raise RuntimeError("PyWin32 is required for OfflineTTS (SAPI).") from e

# --- Одноразово покажемо, звідки нас завантажили (для діагностики шляху) ---
try:
    print(f"[OfflineTTS LOADED: {__file__}]")
except Exception:
    pass

# ---------- Singleton (у межах процесу) ----------
_ENGINE = None                 # SAPI.SpVoice
_INITED = False
_CURRENT_VOICE_NAME = None     # напр., 'natalia'
_CURRENT_VOICE_ID = None       # повний SAPI Id
_LOCK = threading.RLock()      # потокобезпека

# ---------- Процес-глобальні запобіжники через builtins ----------
if not hasattr(builtins, "_LASTIVKA_OFFLINETTS_LOCK"):
    builtins._LASTIVKA_OFFLINETTS_LOCK = threading.RLock()  # type: ignore[attr-defined]
if not hasattr(builtins, "_LASTIVKA_OFFLINETTS_LOGGED"):
    builtins._LASTIVKA_OFFLINETTS_LOGGED = False            # type: ignore[attr-defined]
if not hasattr(builtins, "_LASTIVKA_OFFLINETTS_LAST_TS"):
    builtins._LASTIVKA_OFFLINETTS_LAST_TS = 0.0             # type: ignore[attr-defined]

# ---------- Міжпроцесний анти-дубль: Windows Named Mutex ----------
_MUTEX_NAME = "Global\\Lastivka_OfflineTTS_LogOnce"
_MUTEX_HANDLE = None

def _acquire_mutex() -> bool:
    """Пробуємо зайти в критичну секцію для логування між процесами."""
    global _MUTEX_HANDLE
    try:
        _MUTEX_HANDLE = win32event.CreateMutex(None, False, _MUTEX_NAME)
        rc = win32event.WaitForSingleObject(_MUTEX_HANDLE, 0)
        return rc in (win32con.WAIT_OBJECT_0, win32con.WAIT_ABANDONED)
    except Exception:
        return False

def _release_mutex() -> None:
    """Акуратно відпускаємо м’ютекс (не тримаємо його до кінця життя процесу)."""
    global _MUTEX_HANDLE
    if _MUTEX_HANDLE:
        try:
            win32event.ReleaseMutex(_MUTEX_HANDLE)
            win32api.CloseHandle(_MUTEX_HANDLE)
        except Exception:
            pass
        _MUTEX_HANDLE = None

atexit.register(_release_mutex)

# ---------- Helpers ----------
def _ensure_com_init():
    # MTA краще для різнопотокових сценаріїв; падаємо назад на звичайний CoInitialize
    try:
        pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
    except Exception:
        try:
            pythoncom.CoInitialize()
        except pythoncom.com_error:
            pass  # уже ініціалізовано у цьому треді

def _select_voice_obj(engine, pref_name: str | None):
    """Повертає SAPI voice object за частковим збігом (case-insensitive).
    Якщо не знайдено — повертає поточний голос."""
    voices = engine.GetVoices()
    if pref_name:
        needle = pref_name.lower()
        for i in range(voices.Count):
            v = voices.Item(i)
            try:
                name = v.GetAttribute("Name")
            except Exception:
                name = ""
            if name and needle in name.lower():
                return v
    return engine.Voice  # fallback: не міняємо голос

# мінімальний інтервал між логами (анти-бряцання), сек
_MIN_LOG_INTERVAL = 0.30

def _log_voice_once(engine) -> None:
    """Гарантує один лог на процес; між процесами — через Mutex; плюс rate-limit."""
    global _CURRENT_VOICE_NAME, _CURRENT_VOICE_ID

    # дає можливість тимчасово вимкнути лог під час раннього старту
    if os.environ.get("LASTIVKA_SUPPRESS_TTS_LOG", "0") == "1":
        return

    now = time.monotonic()
    with builtins._LASTIVKA_OFFLINETTS_LOCK:  # type: ignore[attr-defined]
        # якщо вже логували — виходимо
        if getattr(builtins, "_LASTIVKA_OFFLINETTS_LOGGED", False):
            return
        # дуже близькі подвійні виклики — ігноруємо другий
        if (now - float(getattr(builtins, "_LASTIVKA_OFFLINETTS_LAST_TS", 0.0))) < _MIN_LOG_INTERVAL:
            return

        # міжпроцесний gate
        got_mutex = _acquire_mutex()
        try:
            if not got_mutex:
                # інший процес уже встиг залогувати — не дублюємо
                builtins._LASTIVKA_OFFLINETTS_LOGGED = True  # type: ignore[attr-defined]
                return

            v = engine.Voice
            try:
                name = v.GetAttribute("Name")
            except Exception:
                name = None
            _CURRENT_VOICE_NAME = name or "default"
            try:
                _CURRENT_VOICE_ID = v.Id
            except Exception:
                _CURRENT_VOICE_ID = "unknown"

            # позначаємо час ДО друку, щоб навіть якщо print двічі викличеться — другий відсіявся
            builtins._LASTIVKA_OFFLINETTS_LAST_TS = now  # type: ignore[attr-defined]
            print(f"[OfflineTTS pid={os.getpid()}] voice \u2192 {_CURRENT_VOICE_NAME} ({_CURRENT_VOICE_ID})")
            builtins._LASTIVKA_OFFLINETTS_LOGGED = True  # type: ignore[attr-defined]
        finally:
            if got_mutex:
                _release_mutex()

# ---------- Public API ----------
def init_tts_once(preferred_voice: str = "natalia"):
    """Ініціалізує SpVoice один раз (thread-safe). ЛОГ ТУТ НЕ ДРУКУЄМО!"""
    global _ENGINE, _INITED
    if _INITED and _ENGINE is not None:
        return _ENGINE
    with _LOCK:
        if _INITED and _ENGINE is not None:
            return _ENGINE
        _ensure_com_init()
        engine = Dispatch("SAPI.SpVoice")
        # Вибір голосу тільки під час ПЕРШОЇ ініціалізації
        try:
            target = _select_voice_obj(engine, preferred_voice)
            if target is not None:
                engine.Voice = target
        except Exception:
            pass  # залишаємо системний дефолт
        _ENGINE = engine
        _INITED = True
        return _ENGINE  # важливо: БЕЗ _log_voice_once тут

def set_voice(name: str) -> None:
    """Змінює голос лише якщо інший; тоді лог — один раз (lazy)."""
    global _ENGINE, _CURRENT_VOICE_NAME
    engine = init_tts_once()
    target = _select_voice_obj(engine, name)
    try:
        new_name = target.GetAttribute("Name")
    except Exception:
        new_name = None
    if new_name and new_name != _CURRENT_VOICE_NAME:
        with _LOCK:
            engine.Voice = target
            # Дозволяємо один новий лог, бо голос справді змінився
            try:
                with builtins._LASTIVKA_OFFLINETTS_LOCK:       # type: ignore[attr-defined]
                    builtins._LASTIVKA_OFFLINETTS_LOGGED = False  # type: ignore[attr-defined]
                    builtins._LASTIVKA_OFFLINETTS_LAST_TS = 0.0   # скидаємо rate-limit
            except Exception:
                pass
            _log_voice_once(engine)

def speak(text: str, flags: int = 0) -> None:
    """Озвучує текст. flags=0 — синхронний; 1 = SVSFlagsAsync — асинхронний.
    Лог голосу відбувається ЛИШЕ при першому speak() за процес."""
    engine = init_tts_once()
    _log_voice_once(engine)  # lazy-лог тут
    engine.Speak(text, flags)

# --------- Backward-compat aliases ----------
def init_tts(preferred_voice: str = "natalia"):
    return init_tts_once(preferred_voice)

def tts_say(text: str, flags: int = 0):
    return speak(text, flags)

__all__ = [
    "init_tts_once", "set_voice", "speak",
    "init_tts", "tts_say"
]

# --- Import dedup (зшиває різні шляхи імпорту до однієї інстанції) ---
try:
    me = sys.modules.get(__name__)
    for key in ("lastivka_core.speech.offline_tts", "speech.offline_tts", __name__):
        sys.modules[key] = me
except Exception:
    pass
