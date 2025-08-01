from __future__ import annotations
from pathlib import Path
from datetime import datetime
from typing import Callable, Dict, Any

# === Утиліти ===

def _show_log_tail(log_file: Path, say: Callable[[str], None], n: int = 20) -> None:
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()[-n:]
        print("\n".join(line.rstrip("\n") for line in lines))
    except Exception as e:
        say(f"Не вдалося прочитати лог: {e}")

def _status_text(CFG, tts_backend_module: str, LOG_FILE: Path, CONFIG_DIR: Path) -> str:
    return "\n".join([
        f"👤 Ім'я: {CFG.name}",
        f"🔈 Звук: {'вимкнено' if CFG.mute else 'увімкнено'}",
        f"🧠 Емоційний конфіг: {'є' if (CONFIG_DIR/'emotion_config.json').exists() else 'нема'}",
        f"🗣️ TTS backend: {tts_backend_module}",
        f"🗂️ Лог: {LOG_FILE}"
    ])

# === Команди ===

def _cmd_mute_on(CFG, say, *_):
    CFG.mute = True
    say("🔕 Звук вимкнено.")

def _cmd_mute_off(CFG, say, *_):
    CFG.mute = False
    say("🔔 Звук увімкнено.")

def _cmd_log(CFG, say, LOG_FILE: Path, *_):
    say(f"Показую останні 20 рядків логу: {LOG_FILE.name}")
    _show_log_tail(LOG_FILE, say)

def _cmd_status(CFG, say, LOG_FILE: Path, CONFIG_DIR: Path):
    try:
        tts_backend = say.__module__
    except Exception:
        tts_backend = "unknown"
    say("Статус системи.")
    print(_status_text(CFG, tts_backend, LOG_FILE, CONFIG_DIR))

def _cmd_exit(*_):
    raise SystemExit(0)

def _cmd_cover_on(CFG, say, *_):
    CFG.name = CFG.alt_name
    say(f"🛡️ Змінено ідентичність. Тепер я — {CFG.alt_name}.")

def _cmd_time(CFG, say, *_):
    say(f"Зараз {datetime.now().strftime('%H:%M:%S')}.")

def _cmd_date(CFG, say, *_):
    say(f"Сьогодні {datetime.now().strftime('%d.%m.%Y')}.")

def _cmd_help(CFG, say, *_):
    say("Можу: сказати час, дату, статус, керувати звуком, пам'ятати і пригадати.")

def _cmd_weather_stub(CFG, say, *_):
    say("Погода недоступна офлайн. Можу сказати час і дату.")

COMMANDS: Dict[str, Callable[[Any, Callable[[str], None], Path, Path], None]] = {
    "без звуку": _cmd_mute_on,
    "mute": _cmd_mute_on,
    "поверни звук": _cmd_mute_off,
    "звук": _cmd_mute_off,
    "unmute": _cmd_mute_off,
    "лог": _cmd_log,
    "журнал": _cmd_log,
    "стан": _cmd_status,
    "вийти": _cmd_exit,
    "ввімкни прикриття": _cmd_cover_on,
    "час": _cmd_time,
    "дата": _cmd_date,
    "допомога": _cmd_help,
    "погода": _cmd_weather_stub,
}

# === Інтенти високого рівня ===

def handle_intents(user_input: str,
                   CFG,
                   say: Callable[[str], None],
                   CORE_IDENTITY: dict,
                   recall_memory: Callable[[], str | None],
                   remember_memory: Callable[[str], None]) -> bool:
    text = user_input.lower()

    if CFG.activation and user_input.strip() == CFG.activation:
        CFG.name = CORE_IDENTITY.get("Ім'я", "Софія")
        say("⚡️ Ядро Софії Ω активовано.")
        return True

    if user_input.startswith("запам'ятай:"):
        thought = user_input.replace("запам'ятай:", "").strip()
        remember_memory(thought)
        say("Я запам'ятала це.")
        return True

    if "що я тобі казав" in text:
        memory = recall_memory()
        say(memory if memory else "У памʼяті поки нічого немає.")
        return True

    return False
