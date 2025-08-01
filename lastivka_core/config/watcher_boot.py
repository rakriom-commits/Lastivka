# config/watcher_boot.py
import sys
import threading
import time
import json
from pathlib import Path
from importlib import import_module

# === Шляхи та sys.path ===
BASE_DIR = Path(__file__).resolve().parent.parent  # C:\Lastivka\lastivka_core
sys.path.append(str(BASE_DIR))

# === Імпорти залежностей ===
from tools.speech_utils import speak
from tools.emotion_engine import set_emotion, get_emotion

# === Пошук monitor_files у config/tools ===
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

# === Логи безпеки ===
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
SECURITY_LOG = LOGS_DIR / "security_events.json"

# === Антиспам сповіщень ===
MIN_INTERVAL_SEC = 30
_last_alert = {"ts": 0.0}

# === Автовідкат емоції ===
AUTO_RESET_SEC = 60

def _log_event(event: dict):
    try:
        if SECURITY_LOG.exists():
            data = json.loads(SECURITY_LOG.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                data = []
        else:
            data = []
        data.append(event)
        SECURITY_LOG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        # лог не критичний — не блокуємо виконання
        pass

def _reset_emotion_after_delay():
    time.sleep(AUTO_RESET_SEC)
    emo = get_emotion().get("emotion")
    if emo and emo != "спокій":
        try:
            set_emotion("спокій")
        except Exception:
            pass

def _on_change(file_path: Path):
    now = time.time()
    if now - _last_alert["ts"] < MIN_INTERVAL_SEC:
        return
    _last_alert["ts"] = now

    _log_event({
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "file": str(file_path),
        "event": "changed"
    })

    try:
        if file_path.name == "memory_store.json":
            set_emotion("страх")
            speak("⚠️ Попередження. Зовнішня зміна памʼяті виявлена. Я в безпеці?")
        else:
            set_emotion("подив")
            speak(f"Виявлено зміну у файлі {file_path.name}.")
    except Exception:
        pass

    threading.Thread(target=_reset_emotion_after_delay, daemon=True).start()

def start():
    # запуск монітора у фоновому потоці
    t = threading.Thread(target=monitor_files, kwargs={"on_change_callback": _on_change}, daemon=True)
    t.start()
    return t
