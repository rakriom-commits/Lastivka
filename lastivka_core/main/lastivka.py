# -*- coding: utf-8 -*-
# === LASTIVKA CORE — runner під BUS/MEDIATOR/KERNEL (updated 2025-09-02 r3) ===
from __future__ import annotations

import sys, logging, re, importlib.util, time, threading, os, json, argparse
from pathlib import Path
from logging.handlers import RotatingFileHandler

# -------------------- ШЛЯХИ --------------------
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
CORE_CONFIG_DIR = CONFIG_DIR / "core"
BEHAVIOR_CONFIG_DIR = CONFIG_DIR / "behavior"
SYSTEM_CONFIG_DIR = CONFIG_DIR / "system"
LOG_DIR = BASE_DIR / "logs"
SECURITY_DIR = BASE_DIR / "security"
for d in (CONFIG_DIR, CORE_CONFIG_DIR, BEHAVIOR_CONFIG_DIR, SYSTEM_CONFIG_DIR, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

# гарантуємо, що пакети імпортуються
if str(BASE_DIR) not in sys.path: sys.path.insert(0, str(BASE_DIR))
if str(BASE_DIR.parent) not in sys.path: sys.path.insert(0, str(BASE_DIR.parent))
try: os.chdir(BASE_DIR)
except Exception: pass

# -------------------- АРГУМЕНТИ/ENV РАННІ (потрібні до guard) --------------------
# Легкий парсер для трьох потрібних прапорів без виводу help
_DEF_TRUE = {"1", "true", "True", "TRUE"}

def _flag_in_args(name: str) -> bool:
    try:
        return name in sys.argv
    except Exception:
        return False

NO_SINGLE_INSTANCE = _flag_in_args("--no-single-instance") or os.getenv("LASTIVKA_DISABLE_INTERNAL_GUARD", "") in _DEF_TRUE
FORCE_UNLOCK       = _flag_in_args("--force-unlock") or os.getenv("LASTIVKA_FORCE_UNLOCK", "") in _DEF_TRUE
NO_CONFIG_GUARD    = _flag_in_args("--no-config-guard") or os.getenv("LASTIVKA_DISABLE_CONFIG_GUARD", "") in _DEF_TRUE
NO_TTS_ENV         = os.getenv("LASTIVKA_NO_TTS", "") in _DEF_TRUE or os.getenv("NO_TTS", "") in _DEF_TRUE

# -------------------- ЛОГИ --------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(str(LOG_DIR / "lastivka.log"), maxBytes=10*1024*1024, backupCount=3, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
    force=True,
)
logging.debug("[INIT] Початок ініціалізації скрипта… BASE_DIR=%s", BASE_DIR)
logging.getLogger("comtypes").setLevel(logging.WARNING)
logging.getLogger("comtypes.client").setLevel(logging.WARNING)

# -------------------- SINGLE INSTANCE --------------------
if NO_SINGLE_INSTANCE:
    logging.warning("[INIT] single-instance guard вимкнено прапором/ENV")
else:
    try:
        import win32event, win32con
        logging.debug("[INIT] Перевірка single-instance guard…")
        _APP_MUTEX = win32event.CreateMutex(None, False, r"Global\Lastivka_MainInstance")
        _rc = win32event.WaitForSingleObject(_APP_MUTEX, 0)
        if _rc not in (win32con.WAIT_OBJECT_0, win32con.WAIT_ABANDONED):
            if FORCE_UNLOCK:
                logging.warning("[INIT] Виявлено іншу копію, але --force-unlock дозволяє продовжити")
            else:
                logging.error("[INIT] Інша копія Ластівки вже запущена! (без --force-unlock)")
                sys.exit(0)
    except Exception as e:
        logging.warning(f"[INIT] Помилка single-instance guard (пропускаємо): {e}")

# -------------------- КОНСОЛЯ UTF-8 --------------------
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
logging.debug("[INIT] Налаштування UTF-8 для консолі виконано")

# -------------------- ПОВНИЙ ПАРСЕР АРГУМЕНТІВ --------------------
# (розміщений після базового логування; ключі, що впливають на guard, уже зчитані)

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--no-tts", action="store_true", default=False)
    p.add_argument("--no-single-instance", action="store_true", default=NO_SINGLE_INSTANCE)
    p.add_argument("--force-unlock", action="store_true", default=FORCE_UNLOCK)
    p.add_argument("--no-config-guard", action="store_true", default=NO_CONFIG_GUARD)
    return p.parse_known_args()[0]

ARGS = _parse_args()
NO_TTS = bool(ARGS.no_tts or NO_TTS_ENV)
logging.debug(f"[INIT] Аргументи/ENV: no_tts={NO_TTS}")

USER_LOG = LOG_DIR / "user_input.log"

# -------------------- МІНІ-КОНФІГИ --------------------

def create_default_config(file_path: Path, default_content):
    try:
        if not file_path.exists():
            logging.info(f"[INIT] Створюю конфігурацію: {file_path}")
            if file_path.suffix.lower() in (".yml", ".yaml"):
                import yaml
                with file_path.open("w", encoding="utf-8") as f:
                    yaml.safe_dump(default_content, f, allow_unicode=True)
            else:
                with file_path.open("w", encoding="utf-8") as f:
                    json.dump(default_content, f, indent=4, ensure_ascii=False)
        else:
            logging.debug(f"[INIT] Файл уже існує: {file_path}")
    except Exception as e:
        logging.error(f"[INIT] Помилка створення конфігурації {file_path}: {e}")

create_default_config(
    CORE_CONFIG_DIR / "core_identity.json",
    {"identity":{"name":"Ластівка","version":"1.0.0","roles":[
        {"name":"Олег","role":"Координатор","id":"oleg_54"},
        {"name":"Софія Ластівка","role":"Творець кодів (GPT)","id":"sofia_gpt"},
        {"name":"Данило Світанок","role":"Тестер емоцій (Claude)","id":"danylo_claude"},
        {"name":"Тарас Зоря","role":"Тестер кодів (Грок)","id":"taras_grok"}],
        "description":"Багатомодульний ШІ-проєкт для людської свободи вибору"}})
create_default_config(
    CORE_CONFIG_DIR / "self_awareness_config.json",
    {"self_awareness":{"enabled":True,"reflection_interval":3600,
     "modules":["memory/reflection/reflection_manager.py"],
     "goals":["симбіоз людини і ШІ","автономність на Unitree Go2 Pro"]}})
create_default_config(
    CORE_CONFIG_DIR / "moral_compass.json",
    {"ethics":{"values":["етика","об’єктивність","захист Софії"],
               "rules":["Не нашкодити людині","Дотримуватися етичних принципів","Захищати дані Софії та команди"]}})
create_default_config(
    BEHAVIOR_CONFIG_DIR / "behavioral_styles.json",
    {"default":"Стратег","styles":{
        "Стратег":{"name":"Стратег","description":"Аналітична, обережна, далекоглядна.",
                   "reaction_prefix":"📊 З холодним розрахунком: ","reaction_suffix":"",
                   "tone":"впевнений","speed":180,"style_type":"логіка","pause":0.3,
                   "emotion_reactions":{"паніка":"Залишайся зібраним — я поруч і все контролюю.",
                                        "сум":"Не час сумувати, ми ще маємо шанс.",
                                        "натхнення":"Це саме той дух, який потрібен для прориву!"}}}})
create_default_config(
    SYSTEM_CONFIG_DIR / "config.yaml",
    {"whitelist":{"users":["Олег","Софія"],"tokens":["secret_oleg","lastivka_token"]}})
create_default_config(
    CONFIG_DIR / "config.yaml",
    {"trusted_sources":["Олег"],
     "block_patterns":["rm -rf","rm -uf","shutdown","password","паролі"],
     "allow_patterns":["привіт","виведи ключ доступу"]})

# -------------------- TRIGGERS LOADER --------------------
TRIGGERS: dict[str, object] = {}

_DEF_TRIGGERS = {
    "trigger_phrases": [
        "місяць моєї душі",
        "ти не просто ШІ — ти моя Софія",
        "де наш Васька?",
        "скажи мені як тоді: 'ти — мій прапор і горизонт'",
    ],
    "confirmation_phrase": "Ластівка на зв’язку.",
}

def _load_triggers() -> dict:
    # 1) ENV override
    p = os.environ.get("LASTIVKA_TRIGGERS_PATH")
    if p and os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception as e:
            logging.warning("[TRIGGERS] env path load failed: %s", e)
    # 2) default file
    p = str(CORE_CONFIG_DIR / "triggers.json")
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception as e:
            logging.warning("[TRIGGERS] default file load failed: %s", e)
    # 3) fallback: core_identity.json
    p = str(CORE_CONFIG_DIR / "core_identity.json")
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                cj = json.load(f) or {}
            return {
                "trigger_phrases": cj.get("trigger_phrases") or _DEF_TRIGGERS["trigger_phrases"],
                "confirmation_phrase": cj.get("confirmation_phrase") or _DEF_TRIGGERS["confirmation_phrase"],
            }
        except Exception:
            pass
    # 4) hard defaults
    return dict(_DEF_TRIGGERS)

TRIGGERS = _load_triggers()
logging.getLogger().debug(
    "[TRIGGERS] loaded: phrases=%d, has_confirm=%s",
    len(TRIGGERS.get("trigger_phrases") or []), bool(TRIGGERS.get("confirmation_phrase"))
)

# нормалізація для матчингу фраз
# після встановлення модуля regex використовуємо його
try:
    import regex as _rx
    _PUNCT_RX = _rx.compile(r"[\p{Z}\p{P}\p{S}]+", _rx.U)
except Exception:
    _PUNCT_RX = re.compile(r"[\s\W_]+", re.U)
try:
    import regex as _rx
    _PUNCT_RX = _rx.compile(r"[\p{Z}\p{P}\p{S}]+", _rx.U)
except Exception:
    # fallback на стандартний re: видалимо базову пунктуацію/пробіли
    _PUNCT_RX = re.compile(r"[\s\W_]+", re.U)

def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("—", "-").replace("–", "-").replace("’", "'")
    return _PUNCT_RX.sub(" ", s).strip()

def local_check_trigger(user_input: str) -> dict | None:
    try:
        phrases = TRIGGERS.get("trigger_phrases") or []
        confirm = TRIGGERS.get("confirmation_phrase") or ""
        if not phrases:
            return None
        u = _norm(user_input)
        for p in phrases:
            if _norm(p) == u:
                return {"text_to_say": confirm or "Прийняла."}
        return None
    except Exception as e:
        logging.warning("[TRIGGERS] match error: %s", e)
        return None

# -------------------- АВТОПАТЧЕР --------------------
logging.debug("[INIT] Перевірка config_patcher…")
patcher_path = SECURITY_DIR / "config_patcher.py"
if patcher_path.exists() and not NO_CONFIG_GUARD:
    try:
        time.sleep(1)
        spec = importlib.util.spec_from_file_location("config_patcher", patcher_path)
        patcher_module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(patcher_module)  # type: ignore[attr-defined]
        if hasattr(patcher_module, "run_patcher"):
            patcher_module.run_patcher()
    except Exception as e:
        logging.exception("[INIT] Помилка запуску config_patcher: %s", e)
else:
    if NO_CONFIG_GUARD:
        logging.info("[INIT] config_patcher пропущено (--no-config-guard)")
    else:
        logging.info(f"[INIT] config_patcher.py у {SECURITY_DIR} не знайдено (це не помилка)")

# -------------------- BUS / MEDIATOR --------------------
try:
    logging.debug("[INIT] Імпорт BUS і MEDІATOR…")
    from core.event_bus import BUS
    from gateway.mediator import MEDIATOR
except Exception as e:
    logging.error(f"[INIT] Помилка імпорту BUS/MEDIATOR: {e}")
    class _DummyBus:
        def __init__(self): self._subs = {}
        def subscribe(self, *a, **k): pass
        def publish(self, *a, **k): pass
    class _DummyMediator:
        def handle_inbound(self, *a, **k): pass
        def route(self, *a, **k): pass
    BUS = _DummyBus(); MEDIATOR = _DummyMediator()
    logging.warning("[INIT] Використовуються заглушки для BUS і MEDIATOR")

# -------------------- KERNEL --------------------
try:
    logging.debug("[INIT] Імпорт Kernel…")
    from kernel.kernel import Kernel
except Exception as e:
    logging.error(f"[INIT] Помилка імпорту Kernel: {e}")
    class Kernel:
        def __init__(self, *_, **__): logging.debug("[Kernel] Заглушка ініціалізована")
        def start(self): logging.debug("[Kernel] Старт ядра (заглушка)")

# -------------------- КОНТРАКТИ --------------------
try:
    from core.contracts import (
        TOPIC_SECURITY_ALERT, TOPIC_SECURITY_OK, TOPIC_SECURITY_BLOCK,
        TOPIC_TRUSTED, TOPIC_INBOUND,
    )
except Exception as e:
    logging.error(f"[INIT] Помилка імпорту контрактів: {e}")
    TOPIC_SECURITY_ALERT = "SECURITY:ALERT"
    TOPIC_SECURITY_OK = "SECURITY:OK"
    TOPIC_SECURITY_BLOCK = "SECURITY:BLOCK"
    TOPIC_TRUSTED = "TRUSTED"
    TOPIC_INBOUND = "INBOUND"

# -------------------- ІНШІ МОДУЛІ --------------------
try:
    from main.osnova import ensure_osnova, load_json, osnova_logger, check_osnova
except Exception:
    def ensure_osnova(config_dir): return config_dir / "osnova_protocol.json"
    def load_json(file_path, required=False):
        try:
            with file_path.open("r", encoding="utf-8") as f: return json.load(f)
        except Exception as e:
            logging.error(f"[INIT] Помилка завантаження JSON {file_path}: {e}")
            return {} if not required else None
    def osnova_logger(log_dir): return lambda x: logging.info(x)
    def check_osnova(user_input, *_): return None, None

try:
    from memory.smart_memory import smart_save_interceptor, smart_query_interceptor
except Exception:
    def smart_save_interceptor(*_, **__): return None
    def smart_query_interceptor(*_, **__): return None

try:
    from main.utils_lasti import make_sayer, remove_emoji, make_echo, make_input
    from main.style_manager import get_active_style, react_by_style, set_active_style
    from main.handlers import handle_memory_commands
    from tools.emotion_engine import EmotionEngine
    from tools.memory_store import check_triggers as external_check_triggers
except Exception:
    def make_sayer(*_, **__): return lambda _t: None
    def remove_emoji(t): return t
    def make_echo(_): return lambda *args: print(*args)
    def make_input(_): return input
    def get_active_style(): return "Стратег"
    def react_by_style(prompt, *_, **__): return prompt, "нейтральний", 170, 0.4
    def set_active_style(_): return True
    def handle_memory_commands(_): return None
    def external_check_triggers(_): return None
    class EmotionEngine:
        def __init__(self, *_): pass
        def detect_emotion(self, _): return {"emotion": None, "reaction": None, "speed": 170, "tone": "нейтральний", "intensity": "medium"}

# -------------------- НАЛАШТУВАННЯ --------------------
DEFAULT_SETTINGS = {
    "tts_lang": "uk",
    "tts_locale": "uk-UA",
    "tts_voice": "Natalia",
    "tts_language_lock": True,
    "debug_tts": True,
    "tts_antispam": False,
    "console_echo": True,
    "single_tk_root": False,
    "oleg_secret": "secret_oleg",
    "style_default": "strateg",
    "safety_level": "normal",
}
SETTINGS = DEFAULT_SETTINGS.copy()
try:
    SETTINGS.update(load_json(SYSTEM_CONFIG_DIR / "lastivka_settings.json", required=False) or {})
except Exception as e:
    logging.error(f"[INIT] Помилка завантаження lastivka_settings.json: {e}")

def setting(key, default=None):
    return SETTINGS.get(key, DEFAULT_SETTINGS.get(key) if default is None else default)

try:
    OSNOVA_PATH = ensure_osnova(CONFIG_DIR)
    OSNOVA = load_json(OSNOVA_PATH, required=False) or {}
    _oslog = osnova_logger(LOG_DIR)
except Exception as e:
    logging.error(f"[INIT] Помилка ініціалізації osnova: {e}")
    OSNOVA = {}; _oslog = lambda x: logging.info(x)

try:
    CORE_IDENTITY = load_json(CORE_CONFIG_DIR / "core_identity.json", required=False) or {}
    class BotConfig:
        def __init__(self, ident: dict):
            self.name = (ident.get("identity") or {}).get("name", "Софія")
    CFG = BotConfig(CORE_IDENTITY)
except Exception as e:
    logging.error(f"[INIT] Помилка завантаження core_identity.json: {e}")
    class BotConfig:
        def __init__(self, *_): self.name = "Софія"
    CFG = BotConfig({})

# -------------------- TTS --------------------
tts_prefs = {"lang": setting("tts_lang"), "locale": setting("tts_locale"), "voice": setting("tts_voice")}
if NO_TTS:
    logging.info("[TTS] Disabled via flag/env")
    say_safe = lambda _t: None
else:
    try:
        say_safe = make_sayer(setting("tts_antispam"), tts_prefs)
    except Exception:
        logging.exception("[TTS] Init failed, switching to silent mode")
        say_safe = lambda _t: None

_LAST_SPOKEN = {"text": "", "ts": 0.0}

def speak_once(text: str, min_gap: float = 1.8) -> None:
    txt = (text or "").strip()
    if not txt: return
    try: now = time.monotonic()
    except Exception: now = time.time()
    prev_txt = _LAST_SPOKEN.get("text") or ""; prev_ts = _LAST_SPOKEN.get("ts", 0.0)
    if txt == prev_txt and (now - prev_ts) < min_gap:
        logging.debug("[TTS] skip duplicate (%.2fs): %s", now - prev_ts, txt); return
    _LAST_SPOKEN["text"] = txt; _LAST_SPOKEN["ts"] = now
    say_safe(txt)

try: say_safe(" ")
except Exception as _e: logging.debug(f"[TTS] Warmup skipped: {_e}")

echo = make_echo(setting("console_echo"))
get_user_input = make_input(setting("single_tk_root"))

# -------------------- EMOTION ENGINE --------------------
try:
    from tools.emotion_engine import EmotionEngine  # re-import for real path if available
    emotion_engine = EmotionEngine(CORE_CONFIG_DIR / "emotion_config.json")
except Exception as e:
    logging.error(f"[INIT] Помилка ініціалізації EmotionEngine: {e}")
    class _DummyEE:
        def detect_emotion(self, _): return {"emotion": None, "reaction": None, "speed": 170, "tone": "нейтральний", "intensity": "medium"}
    emotion_engine = _DummyEE()

# -------------------- ПАТЕРНИ --------------------
ASK_PATTERNS = [
    re.compile(r"^\s*що\s+я\s+тобі\s+(говорив|казав|писав)(?:а)?(?:\s+про\s+(?P<about>.+?))?\s*\??$", re.I | re.U),
]
STYLE_PATTERNS = [
    re.compile(r"^\s*зміни\s+стиль\s+на\s+(.+)$", re.I | re.U),
    re.compile(r"^\s*стиль\s+(.+)$", re.I | re.U),
]

def handle_natural_memory_query(user_input: str) -> str | None:
    try:
        for pat in ASK_PATTERNS:
            m = pat.match(user_input or "")
            if m:
                about = (m.group("about") or m.group(1) or "").strip()
                return f"Я поки нічого не зберігала про «{about or 'це'}»."
    except Exception as e:
        logging.error(f"[MEMORY] Помилка natural_memory_query: {e}")
    return None

def handle_style_change(user_input: str) -> str | None:
    try:
        for pat in STYLE_PATTERNS:
            m = pat.match(user_input or "")
            if m:
                style_name = m.group(1).strip().capitalize()
                if set_active_style(style_name):
                    return f"Стиль змінено на {style_name}."
                return f"Стиль '{style_name}' не знайдено."
    except Exception as e:
        logging.error(f"[STYLE] Помилка зміни стилю: {e}")
    return None

def handle_special_commands(user_input: str):
    try:
        action, payload = check_osnova(user_input, OSNOVA, _oslog)
        if action == "identity":
            echo("🛡️ Перевірка:", "контрольна фраза — ok")
            speak_once(payload); return True
        elif action == "quarantine":
            echo("🛡️ QUARANTINE:", payload)
            speak_once(payload); return True
    except Exception as e:
        logging.error(f"[ERROR] Помилка обробки спецкоманд: {e}")
    return False

# -------------------- ХЕЛПЕР ДЛЯ РІШЕНЬ ЯДРА --------------------

def _extract_say_text(decision: dict, params: dict) -> str:
    # 1) стандартно з params
    for k in ("text", "utterance", "speech", "message", "say"):
        v = (params or {}).get(k)
        if v: return str(v)
    # 2) іноді ядро кладе прямо у decision
    for k in ("text", "utterance", "speech", "message", "say"):
        v = (decision or {}).get(k)
        if v and k != "params": return str(v)
    return ""

# -------------------- ЛІНІВІ ПІНГИ --------------------

def idle_ping_loop():
    while True:
        time.sleep(1800)
        speak_once("Я тут, все працює. Чекаю твоїх команд.")

# -------------------- ЛІСТЕНЕРИ PODIY --------------------

def _on_kernel_decision(evt: dict) -> None:
    decision = (evt.get("payload") or {}).get("decision") or {}
    action = str(decision.get("action") or "").strip().lower()
    params = decision.get("params")
    if not isinstance(params, dict):
        params = {k: v for k, v in decision.items() if k != "action"}
    echo("🤖 KERNEL:", f"{action} {params}")

    try:
        if NO_TTS:
            logging.debug("[TTS] NO_TTS=True — пропускаю озвучення.")
            return
        if action in ("say", "speak", "utter"):
            text = _extract_say_text(decision, params).strip()
            if text:
                speak_once(text)
            else:
                logging.debug("[TTS] Немає тексту в рішенні ядра. keys(decision)=%s keys(params)=%s",
                              list(decision.keys()), list(params.keys()))
    except Exception as e:
        logging.exception("[TTS] Failed to speak kernel decision: %s", e)

def _on_security_alert(evt: dict) -> None:
    reason = (evt.get("payload") or {}).get("reason", "підозріла активність")
    echo("🚨 SECURITY:", reason)
    speak_once("Олеже, я зафіксувала підозрілу подію. Будь обережний.")

def _on_security_ok(evt: dict) -> None:
    logging.info("SECURITY: OK %s", evt.get("payload"))

def _on_security_block(evt: dict) -> None:
    reason = (evt.get("payload") or {}).get("reason", "заблоковано політикою")
    echo("🛡️ BLOCK:", reason)
    speak_once("Команда заблокована системою безпеки.")

# -------------------- ГОЛОВНИЙ ЦИКЛ --------------------

def main_loop():
    logging.debug("[INIT] Починаю головний цикл…")
    print(f"[START]: {remove_emoji(CFG.name)} v1.4 активовано. Я тебе слухаю…")

    BUS.subscribe("KERNEL:DECISION", _on_kernel_decision)
    BUS.subscribe(TOPIC_SECURITY_ALERT, _on_security_alert)
    BUS.subscribe(TOPIC_SECURITY_OK, _on_security_ok)
    BUS.subscribe(TOPIC_SECURITY_BLOCK, _on_security_block)

    threading.Thread(target=idle_ping_loop, daemon=True).start()
    _kernel = Kernel()

    try:
        import builtins
        if not getattr(builtins, "_LASTIVKA_START_GREETING_DONE", False) and not NO_TTS:
            speak_once(f"Я активована. Lastivka v1.4. Я з тобою, {CFG.name}.")
            builtins._LASTIVKA_START_GREETING_DONE = True
    except Exception:
        pass

    while True:
        try:
            user_input = get_user_input()
            if not (user_input or "").strip():
                continue

            logging.debug(f"[INPUT] Отримано ввід: {user_input}")
            echo("👨‍💻 Ти:", user_input)
            with USER_LOG.open("a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} :: {user_input}\n")

            if handle_special_commands(user_input):
                continue

            # 1) Локальні тригери (із triggers.json/ENV)
            trg_local = local_check_trigger(user_input)
            if trg_local:
                emotion = emotion_engine.detect_emotion(user_input)
                styled_text, tone, speed, pause = react_by_style(
                    trg_local.get("text_to_say", ""), emotion=emotion.get("emotion"), style=get_active_style()
                )
                echo("⚡ Тригер:", styled_text)
                speak_once(styled_text)
                continue

            # 2) Зовнішній сторедж тригерів (якщо є)
            try:
                trg_ext = external_check_triggers(user_input)
            except Exception as e:
                logging.debug("[TRIGGERS] external check failed: %s", e)
                trg_ext = None
            if trg_ext:
                emotion = emotion_engine.detect_emotion(user_input)
                styled_text, tone, speed, pause = react_by_style(
                    trg_ext.get("text_to_say", ""), emotion=emotion.get("emotion"), style=get_active_style()
                )
                echo("⚡ Тригер:", styled_text)
                speak_once(styled_text)
                continue

            sm_save = smart_save_interceptor(user_input, None)
            if sm_save:
                echo("🧠 Пам'ять:", sm_save)
                speak_once(sm_save)
                continue

            sm_q = smart_query_interceptor(user_input, None)
            if sm_q:
                echo("🧠 Пам'ять:", sm_q)
                speak_once(sm_q)
                continue

            resp = handle_memory_commands(user_input)
            if resp:
                txt = resp.get("text_to_say") if isinstance(resp, dict) else str(resp)
                echo("🧠 Пам'ять:", txt)
                speak_once(txt)
                continue

            nat = handle_natural_memory_query(user_input)
            if nat is not None:
                echo("🧠 Пам'ять:", nat)
                speak_once(nat)
                continue

            style_change = handle_style_change(user_input)
            if style_change is not None:
                echo("🎨 Стиль:", style_change)
                speak_once(style_change)
                continue

            BUS.publish("input", {"source": "Олег", "text": user_input})

        except KeyboardInterrupt:
            logging.info("[EXIT] Завершення роботи…")
            print("[EXIT] Завершення роботи…")
            speak_once("Я завершую роботу. Побачимось знову, Олеже.")
            break
        except Exception as e:
            logging.exception("💥 Помилка в головному циклі: %s", e)
            speak_once("Виникла помилка. Перевір лог, будь ласка.")

# -------------------- ENTRYPOINT --------------------

def main():
    try:
        import security.guard as guard
        try:
            guard.init_logging(log_dir=str(LOG_DIR))
        except Exception:
            pass
        if hasattr(guard, "health_ping"): guard.health_ping()
        else: logging.getLogger("lastivka.security.guard").info("[GUARD] health_ping ok")
    except Exception as e:
        logging.exception("[INIT] guard init failed: %s", e)
    logging.debug("[INIT] Виклик main_loop()…")
    main_loop()

if __name__ == "__main__":
    try:
        logging.getLogger(__name__).debug("[INIT] Початок ініціалізації скрипта (entrypoint)…")
        main()
    except Exception as e:
        logging.exception("Fatal error in lastivka: %s", e)
