# speech/voice_module.py — SHIM: якщо онлайн вимкнено, говоримо через офлайн fast (SAPI/RHVoice)
import os, logging
log = logging.getLogger("voice_shim")

_FORCE_OFFLINE = os.getenv("LASTIVKA_TTS_DISABLE_ONLINE") == "1" or os.getenv("LASTIVKA_FORCE_OFFLINE") == "1"

if _FORCE_OFFLINE:
    from speech import voice_module_fast as _fast
    log.info("[voice_shim] ONLINE disabled → using voice_module_fast")
    def is_ready(): 
        return getattr(_fast, "is_ready", lambda: True)()
    def speak(text, *a, **kw):
        return _fast.speak(text, *a, **kw)
else:
    # звичайний онлайн-модуль (якщо десь знадобиться)
    from importlib import import_module as _imp
    _online = _imp("speech.voice_module")   # якщо є справжній онлайн-модуль в іншому пакеті — підкоригуй тут
    is_ready = getattr(_online, "is_ready", lambda: True)
    speak    = getattr(_online, "speak")
