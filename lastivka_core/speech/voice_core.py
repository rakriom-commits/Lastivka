from pathlib import Path
import json, logging, importlib

from speech.voice_dispatcher import speak_with_emotion as _backend_speak

BASE_DIR = Path(__file__).resolve().parents[1]   # ...\lastivka_core
CONFIG_DIR = BASE_DIR / "config"
SETTINGS_PATH = CONFIG_DIR / "lastivka_settings.json"

def _load_settings():
    def _safe(v, default=None):
        return v if v not in ("", None) else default
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    return {
        "primary": {
            "lang":   _safe(data.get("tts_lang"),   "uk"),
            "locale": _safe(data.get("tts_locale"), "uk-UA"),
            "voice":  _safe(data.get("tts_voice"),  None),
        },
        "fallback": {
            "lang":   _safe(data.get("tts_fallback_lang"),   "en"),
            "locale": _safe(data.get("tts_fallback_locale"), "en-US"),
            "voice":  _safe(data.get("tts_fallback_voice"),  None),
        },
        "language_lock": bool(data.get("tts_language_lock", True)),
        "debug_tts": bool(data.get("debug_tts", True)),
    }

_CFG = _load_settings()
_LOGGED = {"primary": False, "fallback": False}

# --------- ГЛИБОКИЙ форс налаштувань у speech.voice_dispatcher (якщо він щось з цього вміє)
def _deep_force_dispatcher(prefs: dict):
    """
    Прагматично: ліземо у модуль speech.voice_dispatcher і намагаємось
    задати мову/голос будь-яким із доступних способів:
      - глобальні змінні (LANG, LANGUAGE, CURRENT_LANG, VOICE_NAME, VOICE)
      - функції set_lang/set_locale/set_voice
      - якщо є engine (pyttsx3) — підбираємо голос за lang/locale/voice
    Усе в try/except — нічого не ламаємо.
    """
    try:
        disp = importlib.import_module("speech.voice_dispatcher")
    except Exception as e:
        if _CFG["debug_tts"]:
            logging.debug(f"[VoiceCore] dispatcher import fail: {e}")
        return

    lang = prefs.get("lang"); locale = prefs.get("locale"); voice = prefs.get("voice")

    # 1) Спроба через функції
    try:
        if hasattr(disp, "set_lang") and lang:
            disp.set_lang(lang)
        if hasattr(disp, "set_locale") and locale:
            disp.set_locale(locale)
        if hasattr(disp, "set_voice") and voice:
            disp.set_voice(voice)
    except Exception as e:
        if _CFG["debug_tts"]:
            logging.debug(f"[VoiceCore] dispatcher setters fail: {e}")

    # 2) Спроба через очевидні глобалі
    try:
        for name, val in {
            "LANG": lang, "LANGUAGE": lang, "CURRENT_LANG": lang, "TTS_LANG": lang,
            "LOCALE": locale, "TTS_LOCALE": locale,
            "VOICE": voice, "VOICE_NAME": voice, "TTS_VOICE": voice
        }.items():
            if val and hasattr(disp, name):
                setattr(disp, name, val)
    except Exception:
        pass

    # 3) Якщо в диспетчера є engine (pyttsx3-подібний), підберемо по мові
    try:
        eng = getattr(disp, "engine", None) or getattr(disp, "tts_engine", None) or getattr(disp, "tts", None)
        if eng:
            # pyttsx3 API: voices = engine.getProperty("voices")
            # Спробуємо за voice name, потім за lang/locale у id або languages
            voices = []
            try:
                voices = eng.getProperty("voices") or []
            except Exception:
                voices = []
            picked_id = None
            if voice:
                for v in voices:
                    # v.name або v.id можуть містити рядок голосу
                    if (getattr(v, "name", "") or "").lower() == voice.lower() or (getattr(v, "id", "") or "").lower().endswith(voice.lower()):
                        picked_id = getattr(v, "id", None); break
            if not picked_id and (lang or locale):
                want = (locale or lang or "").lower()
                for v in voices:
                    meta = f"{getattr(v, 'id','')}|{getattr(v,'languages', '')}|{getattr(v,'name','')}".lower()
                    if want and want in meta:
                        picked_id = getattr(v, "id", None); break
            if picked_id:
                try:
                    eng.setProperty("voice", picked_id)
                    if _CFG["debug_tts"]:
                        logging.info(f"[VoiceCore] engine voice set → {picked_id}")
                except Exception as e:
                    if _CFG["debug_tts"]:
                        logging.debug(f"[VoiceCore] engine.setProperty('voice', ...) fail: {e}")
    except Exception as e:
        if _CFG["debug_tts"]:
            logging.debug(f"[VoiceCore] engine voice pick fail: {e}")

# --------- Т
