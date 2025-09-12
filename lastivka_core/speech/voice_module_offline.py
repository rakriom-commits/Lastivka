import logging
logger = logging.getLogger(__name__)

# Anti-storm для логів (L1/L2)
try:
    from lastivka_core.tools.logging_filters import attach_rate_limit
    attach_rate_limit(logger, lines_per_minute=500, bytes_per_hour=5*1024*1024)
except Exception:
    pass
import time, datetime, json, os
from pathlib import Path
import pyttsx3
import builtins

BASE_DIR = Path(__file__).resolve().parents[1]   # ...\lastivka_core
CFG_PATH = BASE_DIR / "config" / "lastivka_settings.json"
LOG_PATH = BASE_DIR / "logs" / "audio_log.txt"

def _load_cfg():
    try:
        return json.loads(CFG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
CFG = _load_cfg()

# РќР°Р»Р°С€С‚СѓРІР°РЅРЅСЏ
DEBUG = bool(CFG.get("debug_tts", True))
LANG_LOCK = bool(CFG.get("tts_language_lock", True))

PREF_LANG  = (CFG.get("tts_lang")   or "uk").lower()
PREF_LOC   = (CFG.get("tts_locale") or "uk-UA").lower()
PREF_VOICE = (CFG.get("tts_voice")  or "").strip()

FALLBACK_LANG  = (CFG.get("tts_fallback_lang")   or "uk").lower()
FALLBACK_LOC   = (CFG.get("tts_fallback_locale") or "uk-UA").lower()
FALLBACK_VOICE = (CFG.get("tts_fallback_voice")  or "").strip()

# --- РњР°СЂРєРµСЂРё С‚Р° РїСЂС–РѕСЂРёС‚РµС‚Рё
_UK_MARKERS = ("uk", "uk-ua", "uk_ua", "ukrain", "СѓРєСЂР°С—РЅ")
_RU_MARKERS = ("ru", "ru-ru", "ru_ru", "russian", "СЂСѓСЃ")
UA_PREFERRED_NAMES = ("natalia", "ukrainian", "marianna", "volodymyr", "halyna", "marichka")
UA_PREFERRED_TOKENS = ("\\rhvoice\\natalia", "\\rhvoice_uk\\", "\\ukrain", "\\uk-ua")

# Р“Р»РѕР±Р°Р»СЊРЅРёР№ РїСЂР°РїРѕСЂРµС†СЊ (Сѓ РјРµР¶Р°С… РїСЂРѕС†РµСЃСѓ) вЂ” С‰РѕР± РЅРµ РїР»РѕРґРёС‚Рё Р»РѕРіРё
if not hasattr(builtins, "_VMO_VOICE_LOGGED"):
    builtins._VMO_VOICE_LOGGED = False  # type: ignore[attr-defined]

# ---------- Р›РѕРі Сѓ С„Р°Р№Р» (Р±РµР· РєРѕРЅСЃРѕР»С–) ----------
def _log_file(line: str):
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] [offline] {line}\n")
    except Exception:
        pass

def _debug(line: str):
    # Р”РµР±Р°Рі вЂ” С‚С–Р»СЊРєРё Сѓ С„Р°Р№Р». РљРѕРЅСЃРѕР»СЊ РќР• С‡С–РїР°С”РјРѕ.
    if DEBUG:
        _log_file(line)

# ---------- Р†РќР†Р¦Р†РђР›Р†Р—РђР¦Р†РЇ Р”Р’РР“РЈРќРђ (Р· С„РѕР»Р±РµРєРѕРј С– РіСѓС‡РЅС–СЃС‚СЋ)
def _init_engine():
    try:
        eng = pyttsx3.init(driverName="sapi5")  # Windows SAPI5
    except Exception:
        eng = pyttsx3.init()  # РѕСЃС‚Р°РЅРЅС–Р№ С€Р°РЅСЃ
    try:
        eng.setProperty("volume", 1.0)
    except Exception:
        pass
    return eng

engine = _init_engine()

def _norm(s):
    try:
        return str(s).lower()
    except Exception:
        return ""

def _voice_meta(v):
    vid  = _norm(getattr(v, "id", ""))
    vnm  = _norm(getattr(v, "name", ""))
    vlns = getattr(v, "languages", None)
    if isinstance(vlns, (list, tuple)) and vlns:
        try:
            vlns = "|".join([
                _norm(x.decode(errors="ignore") if isinstance(x, (bytes, bytearray)) else x)
                for x in vlns
            ])
        except Exception:
            vlns = ""
    else:
        vlns = ""
    return vid, vnm, vlns

def _score(v, prefer_name=""):
    vid, vnm, vlns = _voice_meta(v)
    meta = f"{vid}|{vnm}|{vlns}"
    score = 0
    # 1) СЏРІРЅРµ С–Рј'СЏ Р· РєРѕРЅС„С–РіСѓ
    if prefer_name and prefer_name.lower() in vnm:
        score += 2000
    # 2) РЅР°С€ СЃРїРёСЃРѕРє РїСЂС–РѕСЂРёС‚РµС‚РЅРёС… СѓРєСЂР°С—РЅСЃСЊРєРёС… РіРѕР»РѕСЃС–РІ
    if any(name in vnm for name in UA_PREFERRED_NAMES):
        score += 1800
    if any(tok in vid for tok in UA_PREFERRED_TOKENS):
        score += 1600
    # 3) РјР°СЂРєРµСЂРё СѓРєСЂР°С—РЅСЃСЊРєРѕС—
    if any(m in meta for m in _UK_MARKERS):
        score += 400
    # 4) Р»РѕРєР°Р»СЊ С‚Р° РјРѕРІР°
    if PREF_LOC and PREF_LOC in meta:
        score += 80
    if PREF_LANG and PREF_LANG in meta:
        score += 60
    # 5) РЅРµ-СЂРѕСЃС–Р№СЃСЊРєС– С‚СЂРѕС…Рё РІРёС‰Рµ
    if not any(m in meta for m in _RU_MARKERS):
        score += 20
    # 6) СЂРѕСЃС–Р№СЃСЊРєС– вЂ” РІРµР»РёРєРёР№ С€С‚СЂР°С„
    if any(m in meta for m in _RU_MARKERS):
        score -= 2000
    return score

def _pick_voice(eng, prefer_name="", want_lang=PREF_LANG, want_loc=PREF_LOC):
    try:
        voices = eng.getProperty("voices") or []
    except Exception:
        voices = []
    if not voices:
        return None

    ranked = sorted(voices, key=lambda v: _score(v, prefer_name), reverse=True)
    best = ranked[0]

    # СЏРєС‰Рѕ best вЂ” RU, С€СѓРєР°С”РјРѕ РїРµСЂС€РёР№ РЅРµ-RU
    b_id, b_nm, b_ln = _voice_meta(best)
    if any(m in f"{b_id}|{b_nm}|{b_ln}" for m in _RU_MARKERS):
        for v in ranked:
            vid, vnm, vln = _voice_meta(v)
            if not any(m in f"{vid}|{vnm}|{vln}" for m in _RU_MARKERS):
                best = v
                break
    return best

def _apply_voice(eng, v):
    try:
        eng.setProperty("voice", getattr(v, "id"))
        return True
    except Exception:
        return False

def _ensure_voice(eng, primary=True):
    """Р’СЃС‚Р°РЅРѕРІР»СЋС” РіРѕР»РѕСЃ Р±РµР· РґСЂСѓРєСѓ РІ РєРѕРЅСЃРѕР»СЊ. РџРёС€Рµ Сѓ С„Р°Р№Р» Р»РёС€Рµ РїРµСЂС€РёР№ СЂР°Р·."""
    name = PREF_VOICE if primary else FALLBACK_VOICE
    v = _pick_voice(eng, prefer_name=name)
    if v and _apply_voice(eng, v):
        if not builtins._VMO_VOICE_LOGGED:  # type: ignore[attr-defined]
            vid, vnm, vln = _voice_meta(v)
            _debug(f"voice в†’ {vnm} ({vid}) [primary={primary}]")
            builtins._VMO_VOICE_LOGGED = True  # type: ignore[attr-defined]
        return True

    v = _pick_voice(eng, prefer_name="")
    if v and _apply_voice(eng, v):
        if not builtins._VMO_VOICE_LOGGED:  # type: ignore[attr-defined]
            vid, vnm, vln = _voice_meta(v)
            _debug(f"voice(any non-RU) в†’ {vnm} ({vid})")
            builtins._VMO_VOICE_LOGGED = True  # type: ignore[attr-defined]
        return True

    # РѕСЃС‚Р°РЅРЅС–Р№ С€Р°РЅСЃ вЂ” РїРµСЂС€РёР№ РґРѕСЃС‚СѓРїРЅРёР№
    try:
        vs = eng.getProperty("voices") or []
        if vs and _apply_voice(eng, vs[0]):
            if not builtins._VMO_VOICE_LOGGED:  # type: ignore[attr-defined]
                vid, vnm, vln = _voice_meta(vs[0])
                _debug(f"voice(fallback first) в†’ {vnm} ({vid})")
                builtins._VMO_VOICE_LOGGED = True  # type: ignore[attr-defined]
            return True
    except Exception:
        pass
    return False

# РїРµСЂРІРёРЅРЅРёР№ РІРёР±С–СЂ РїСЂРё С–РјРїРѕСЂС‚С– (РјРѕРІС‡РєРё, Р±РµР· РєРѕРЅСЃРѕР»С–)
_ensure_voice(engine, primary=True)

# ---------- РњРђРџРђ РЁР’РР”РљРћРЎРўР•Р™
STYLE_MAP = {
    "РЅР°С‚С…РЅРµРЅРЅСЏ": {"rate": 210}, "СЃРјСѓС‚РѕРє": {"rate": 140}, "СЃРїРѕРєС–Р№": {"rate": 160},
    "СЂР°РґС–СЃС‚СЊ": {"rate": 190}, "Р·Р»С–СЃС‚СЊ": {"rate": 150}, "РїРѕРґРёРІ": {"rate": 180},
    "СЃС‚СЂР°С…": {"rate": 160}, "РіРѕСЂРґС–СЃС‚СЊ": {"rate": 200}, "РІРґСЏС‡РЅС–СЃС‚СЊ": {"rate": 170},
    "Р»СЋР±РѕРІ": {"rate": 130}, "СЃРѕСЂРѕРј": {"rate": 165}
}

def _log(text):
    _log_file(text)

def _hot_reset_engine():
    global engine
    try:
        engine.stop()
    except Exception:
        pass
    engine = _init_engine()
    _ensure_voice(engine, primary=True)

def speak(text, emotion=None, tone=None, intensity=None, speed=170, pause=0.0, style=None):
    """РЎС‚С–Р№РєРµ РѕР·РІСѓС‡РµРЅРЅСЏ Р· Р°РІС‚РѕРїРµСЂРµРІСЃС‚Р°РЅРѕРІР»РµРЅРЅСЏРј РіРѕР»РѕСЃСѓ С– РіР°СЂСЏС‡РёРј СЂРµ-С–РЅС–С‚РѕРј."""
    if not text or not str(text).strip():
        return
    try:
        if LANG_LOCK:
            ok = _ensure_voice(engine, primary=True)
            if not ok:
                _ensure_voice(engine, primary=False)

        if pause and pause > 0:
            time.sleep(pause)

        if style and style in STYLE_MAP:
            try:
                engine.setProperty("rate", STYLE_MAP[style]["rate"])
            except Exception:
                pass
        else:
            try:
                engine.setProperty("rate", int(speed))
            except Exception:
                pass

        engine.say(str(text))
        engine.runAndWait()

        if pause and pause > 0.2:
            time.sleep(pause * 0.8)

        _log(text)

    except RuntimeError:
        _hot_reset_engine()
        try:
            engine.say(str(text))
            engine.runAndWait()
            _log(text)
        except Exception as e2:
            _debug(f"РџС–СЃР»СЏ СЂРµ-С–РЅС–С‚Сѓ С‚РµР¶ Р·Р±С–Р№: {e2}")
    except Exception as e:
        _debug(f"РџРѕРјРёР»РєР° РїС–Рґ С‡Р°СЃ РѕР·РІСѓС‡РµРЅРЅСЏ: {e}")
        _debug(f"РќРµРІРґР°Р»РёР№ С‚РµРєСЃС‚: {text}")

