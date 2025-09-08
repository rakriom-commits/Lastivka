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

# Налаштування
DEBUG = bool(CFG.get("debug_tts", True))
LANG_LOCK = bool(CFG.get("tts_language_lock", True))

PREF_LANG  = (CFG.get("tts_lang")   or "uk").lower()
PREF_LOC   = (CFG.get("tts_locale") or "uk-UA").lower()
PREF_VOICE = (CFG.get("tts_voice")  or "").strip()

FALLBACK_LANG  = (CFG.get("tts_fallback_lang")   or "uk").lower()
FALLBACK_LOC   = (CFG.get("tts_fallback_locale") or "uk-UA").lower()
FALLBACK_VOICE = (CFG.get("tts_fallback_voice")  or "").strip()

# --- Маркери та пріоритети
_UK_MARKERS = ("uk", "uk-ua", "uk_ua", "ukrain", "україн")
_RU_MARKERS = ("ru", "ru-ru", "ru_ru", "russian", "рус")
UA_PREFERRED_NAMES = ("natalia", "ukrainian", "marianna", "volodymyr", "halyna", "marichka")
UA_PREFERRED_TOKENS = ("\\rhvoice\\natalia", "\\rhvoice_uk\\", "\\ukrain", "\\uk-ua")

# Глобальний прапорець (у межах процесу) — щоб не плодити логи
if not hasattr(builtins, "_VMO_VOICE_LOGGED"):
    builtins._VMO_VOICE_LOGGED = False  # type: ignore[attr-defined]

# ---------- Лог у файл (без консолі) ----------
def _log_file(line: str):
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] [offline] {line}\n")
    except Exception:
        pass

def _debug(line: str):
    # Дебаг — тільки у файл. Консоль НЕ чіпаємо.
    if DEBUG:
        _log_file(line)

# ---------- ІНІЦІАЛІЗАЦІЯ ДВИГУНА (з фолбеком і гучністю)
def _init_engine():
    try:
        eng = pyttsx3.init(driverName="sapi5")  # Windows SAPI5
    except Exception:
        eng = pyttsx3.init()  # останній шанс
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
    # 1) явне ім'я з конфігу
    if prefer_name and prefer_name.lower() in vnm:
        score += 2000
    # 2) наш список пріоритетних українських голосів
    if any(name in vnm for name in UA_PREFERRED_NAMES):
        score += 1800
    if any(tok in vid for tok in UA_PREFERRED_TOKENS):
        score += 1600
    # 3) маркери української
    if any(m in meta for m in _UK_MARKERS):
        score += 400
    # 4) локаль та мова
    if PREF_LOC and PREF_LOC in meta:
        score += 80
    if PREF_LANG and PREF_LANG in meta:
        score += 60
    # 5) не-російські трохи вище
    if not any(m in meta for m in _RU_MARKERS):
        score += 20
    # 6) російські — великий штраф
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

    # якщо best — RU, шукаємо перший не-RU
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
    """Встановлює голос без друку в консоль. Пише у файл лише перший раз."""
    name = PREF_VOICE if primary else FALLBACK_VOICE
    v = _pick_voice(eng, prefer_name=name)
    if v and _apply_voice(eng, v):
        if not builtins._VMO_VOICE_LOGGED:  # type: ignore[attr-defined]
            vid, vnm, vln = _voice_meta(v)
            _debug(f"voice → {vnm} ({vid}) [primary={primary}]")
            builtins._VMO_VOICE_LOGGED = True  # type: ignore[attr-defined]
        return True

    v = _pick_voice(eng, prefer_name="")
    if v and _apply_voice(eng, v):
        if not builtins._VMO_VOICE_LOGGED:  # type: ignore[attr-defined]
            vid, vnm, vln = _voice_meta(v)
            _debug(f"voice(any non-RU) → {vnm} ({vid})")
            builtins._VMO_VOICE_LOGGED = True  # type: ignore[attr-defined]
        return True

    # останній шанс — перший доступний
    try:
        vs = eng.getProperty("voices") or []
        if vs and _apply_voice(eng, vs[0]):
            if not builtins._VMO_VOICE_LOGGED:  # type: ignore[attr-defined]
                vid, vnm, vln = _voice_meta(vs[0])
                _debug(f"voice(fallback first) → {vnm} ({vid})")
                builtins._VMO_VOICE_LOGGED = True  # type: ignore[attr-defined]
            return True
    except Exception:
        pass
    return False

# первинний вибір при імпорті (мовчки, без консолі)
_ensure_voice(engine, primary=True)

# ---------- МАПА ШВИДКОСТЕЙ
STYLE_MAP = {
    "натхнення": {"rate": 210}, "смуток": {"rate": 140}, "спокій": {"rate": 160},
    "радість": {"rate": 190}, "злість": {"rate": 150}, "подив": {"rate": 180},
    "страх": {"rate": 160}, "гордість": {"rate": 200}, "вдячність": {"rate": 170},
    "любов": {"rate": 130}, "сором": {"rate": 165}
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
    """Стійке озвучення з автоперевстановленням голосу і гарячим ре-інітом."""
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
            _debug(f"Після ре-ініту теж збій: {e2}")
    except Exception as e:
        _debug(f"Помилка під час озвучення: {e}")
        _debug(f"Невдалий текст: {text}")
