# config/watcher_boot.py
import sys
import threading
import time
import json
from pathlib import Path
from importlib import import_module

# === Корінь проєкту в sys.path ===
# this file is at: lastivka_core/config/watcher_boot.py
BASE_DIR = Path(__file__).resolve().parents[1]  # C:\Lastivka\lastivka_core
sys.path.append(str(BASE_DIR))

# === Імпорти мовлення/емоцій (не фатальні) ===
try:
    from tools.speech_utils import speak
except Exception:
    def speak(*args, **kwargs):  # мʼякий заглушувач
        pass

try:
    from tools.emotion_engine import set_emotion, get_emotion
except Exception:
    def set_emotion(*args, **kwargs):
        pass
    def get_emotion():
        return {"emotion": "спокій"}

# === Завантаження monitor_files з config або tools ===
def _load_monitor():
    for modpath in ("config.file_watcher", "tools.file_watcher"):
        try:
            mod = import_module(modpath)
            if hasattr(mod, "monitor_files"):
                return mod.monitor_files
        except Exception:
            continue
    raise ImportError("monitor_files not found in config.file_watcher or tools.file_watcher")

monitor_files = _load_monitor()

# === Логи ===
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True, parents=True)
SECURITY_LOG = LOGS_DIR / "security_events.json"

def _append_json(path: Path, payload):
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8") or "[]")
            if not isinstance(data, list):
                data = []
        else:
            data = []
        data.append(payload)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        # лог не критичний — ігноруємо
        pass

# === Налаштування сповіщень ===
MIN_INTERVAL_SEC = 30      # тротлінг
AUTO_RESET_SEC = 60        # авто-скидання емоцій
VOICE_ALERTS_ENABLED = False  # 🔇 голосові алерти вимкнено

# Файли, які ігноруємо (службові/шумні)
IGNORE_NAMES = {
    "memory_store.json",          # і в config/, і в logs/
    "core_hash_reference.json",
}

# Розширення, які моніторимо (щоб менше шуму)
WATCH_EXTENSIONS = {".json", ".yaml", ".yml", ".ini", ".cfg"}

_last_alert_ts = 0.0

def _reset_emotion_after_delay():
    time.sleep(AUTO_RESET_SEC)
    try:
        emo = (get_emotion() or {}).get("emotion")
        if emo and emo != "спокій":
            set_emotion("спокій")
    except Exception:
        pass

def _on_change(file_path: Path):
    global _last_alert_ts

    # Прості фільтри шуму
    name = file_path.name
    if name in IGNORE_NAMES:
        return
    if file_path.suffix.lower() not in WATCH_EXTENSIONS:
        return

    now = time.time()
    if (now - _last_alert_ts) < MIN_INTERVAL_SEC:
        return
    _last_alert_ts = now

    # Лог події
    event = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "file": str(file_path),
        "event": "changed",
    }
    _append_json(SECURITY_LOG, event)

    # Акуратна реакція без голосу (за замовчуванням)
    try:
        set_emotion("злість")  # або "смуток" — за бажанням
    except Exception:
        pass

    if VOICE_ALERTS_ENABLED:
        # Без емодзі та зайвої драматургії
        try:
            speak(f"Виявлено зміну у файлі {name}.")
        except Exception:
            pass

    # Мʼяко повертаємо емоцію до «спокій»
    threading.Thread(target=_reset_emotion_after_delay, daemon=True).start()

def start():
    """
    Запускає монітор у фоновому потоці.
    file_watcher.monitor_files(on_change_callback=...)
    має сам слідкувати за config/ та logs/.
    """
    t = threading.Thread(target=monitor_files, kwargs={"on_change_callback": _on_change}, daemon=True)
    t.start()
    return t
