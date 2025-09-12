import logging
logger = logging.getLogger(__name__)

# Anti-storm для логів (L1/L2)
try:
    from lastivka_core.tools.logging_filters import attach_rate_limit
    attach_rate_limit(logger, lines_per_minute=500, bytes_per_hour=5*1024*1024)
except Exception:
    pass
# lastivka_core/speech/voice_module_fast.py
# SAPI (RHVoice/eSpeak/MS) з прогрівом і виміром затримки.
import os, time, threading, logging
_lock = threading.RLock()
log = logging.getLogger("voice_fast")

try: import win32com.client as win32
except Exception: win32=None
try: import pyttsx3
except Exception: pyttsx3=None

_engine=None; _backend=None; _inited=False
_DEFAULT_RATE_SAPI = int(os.getenv("LASTIVKA_TTS_RATE") or 0)  # -10..+10
_DEFAULT_RATE_PY   = 165
_DEFAULT_VOL       = 100
_PREWARM           = os.getenv("LASTIVKA_TTS_PREWARM","1") == "1"  # за замовчуванням вмикаємо

_UA_MARKERS=("uk-ua","uk_ua","ukrain"," ukrain","0x422","uk ")

def _log_sapi_voice(v):
    try:
        t=v.Voice
        lang=""; 
        try: lang=t.GetAttribute("Language")
        except: pass
        log.info("[voice_fast] PICK SAPI: %s | %s | Lang=%s", t.GetDescription(), getattr(t,"Id",""), lang)
    except Exception: pass

def _force_index(v):
    idx=(os.getenv("LASTIVKA_TTS_VOICE_INDEX") or "").strip()
    if idx.isdigit():
        ts=v.GetVoices()
        v.Voice = ts.Item(int(idx)); 
        return True
    return False

def _pick_sapi_by_env(v):
    ts=v.GetVoices()
    hint_id=(os.getenv("LASTIVKA_TTS_VOICE_ID") or "").strip().lower()
    if hint_id:
        for i in range(ts.Count):
            t=ts.Item(i)
            meta=(t.GetDescription()+" | "+str(getattr(t,"Id",""))).lower()
            if hint_id in meta: v.Voice=t; return True
    hint=(os.getenv("LASTIVKA_TTS_VOICE") or "").strip().lower()
    if hint:
        for i in range(ts.Count):
            t=ts.Item(i)
            meta=(t.GetDescription()+" | "+str(getattr(t,"Id",""))).lower()
            if hint in meta: v.Voice=t; return True
    return False

def _pick_sapi_uk(v):
    ts=v.GetVoices()
    # LCID 0x422
    for i in range(ts.Count):
        t=ts.Item(i)
        try: lang=t.GetAttribute("Language") or ""
        except Exception: lang=""
        if "422" in str(lang).lower(): v.Voice=t; return True
    # маркери
    for i in range(ts.Count):
        t=ts.Item(i)
        meta=(t.GetDescription()+" | "+str(getattr(t,"Id",""))).lower()
        if any(m in meta for m in _UA_MARKERS): v.Voice=t; return True
    return False

def _sapi_prewarm(v):
    if not _PREWARM: return
    try:
        old_vol = v.Volume
        v.Volume = 0
        v.Speak(" .")    # дуже короткий sync-тик без звуку
        v.Volume = old_vol
        log.info("[voice_fast] PREWARM done")
    except Exception as e:
        log.warning("[voice_fast] PREWARM failed: %s", e)

def _init_engine(lang="uk"):
    global _engine,_backend,_inited
    if _inited: return
    if win32 is not None:
        try:
            v=win32.Dispatch("SAPI.SpVoice")
            ok = _force_index(v) or _pick_sapi_by_env(v) or _pick_sapi_uk(v)
            v.Rate=_DEFAULT_RATE_SAPI; v.Volume=_DEFAULT_VOL
            _engine,_backend,_inited=v,"sapi",True
            _log_sapi_voice(v)
            _sapi_prewarm(v)    # прогрів одразу після вибору голосу
            return
        except Exception as e:
            log.warning("[voice_fast] SAPI init failed: %s", e)
    if pyttsx3 is not None:
        eng=pyttsx3.init(driverName="sapi5")
        try:
            hint=(os.getenv("LASTIVKA_TTS_VOICE") or "").strip().lower()
            chosen=None
            for vv in eng.getProperty("voices") or []:
                name=(getattr(vv,"name","") or "").lower()
                vid=(getattr(vv,"id","") or "").lower()
                meta=name+" | "+vid
                if (hint and hint in meta) or (not hint and any(m in meta for m in _UA_MARKERS)):
                    chosen=vv.id; break
            if chosen: eng.setProperty("voice", chosen)
        except Exception: pass
        eng.setProperty("rate", _DEFAULT_RATE_PY); eng.setProperty("volume", 1.0)
        _engine,_backend,_inited=eng,"pyttsx3",True
        log.info("[voice_fast] PICK PYTTSX3 (sapi5) voice set=%s", bool(chosen))
        return
    raise RuntimeError("No offline TTS backend (need win32com or pyttsx3)")

def is_ready(): return (win32 is not None) or (pyttsx3 is not None)

def speak(text, lang="uk", slow=False, **kwargs):
    s = (text or "").strip()
    if not s: return
    with _lock:
        _init_engine(lang=lang)
        t0=time.perf_counter()
        if _backend=="sapi":
            try:
                rate=_DEFAULT_RATE_SAPI + (-2 if slow else 0)
                _engine.Rate=max(-10,min(10,rate))
            except Exception: pass
            _engine.Speak(s)     # synch
        else:
            try:
                _engine.setProperty("rate", max(120,_DEFAULT_RATE_PY-40) if slow else _DEFAULT_RATE_PY)
            except Exception: pass
            _engine.say(s); _engine.runAndWait()
        dt=(time.perf_counter()-t0)*1000
        log.info("[voice_fast] SPEAK ms=%.0f text=%.60s", dt, s)

