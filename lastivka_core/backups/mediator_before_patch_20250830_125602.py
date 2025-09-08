# -*- coding: utf-8 -*-
import logging
import re
from pathlib import Path
from typing import Dict, Any, Set
import yaml
from core.event_bus import BUS
from core.contracts import TOPIC_TRUSTED, TOPIC_SECURITY_BLOCK

CONFIG_PATH = Path("config/system/config.yaml")
SECURITY_CONFIG_PATH = Path("config/config.yaml")
SECURITY_LOG_PATH = Path("logs/security.log")  # лишаємо для сумісності/можливого використання

def _load_trusted() -> Set[str]:
    """
    Читає whitelist із config/system/config.yaml:
    whitelist:
      users: ["Олег","Софія"]
      tokens: ["..."]
    Якщо файлу ще нема — дефолт.
    """
    if not CONFIG_PATH.exists():
        logging.warning(f"[MEDIATOR] Конфігурація {CONFIG_PATH} не знайдена, використовую дефолтний whitelist")
        return {"Олег", "Софія"}
    try:
        cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
        wl = cfg.get("whitelist", {})
        users = set(map(str, wl.get("users", [])))
        tokens = set(map(str, wl.get("tokens", [])))
        result = users | tokens
        logging.debug(f"[MEDIATOR] Завантажено довірені джерела: {result}")
        return result
    except Exception as e:
        logging.exception(f"[MEDIATOR] Помилка читання {CONFIG_PATH}: {e}")
        return {"Олег", "Софія"}

def _load_block_patterns() -> list:
    """
    Читає block_patterns із config/config.yaml (може знадобитися для додаткових перевірок).
    """
    if not SECURITY_CONFIG_PATH.exists():
        logging.warning(f"[MEDIATOR] Конфігурація {SECURITY_CONFIG_PATH} не знайдена, використовую порожній список")
        return []
    try:
        cfg = yaml.safe_load(SECURITY_CONFIG_PATH.read_text(encoding="utf-8")) or {}
        patterns = [str(pattern).lower() for pattern in cfg.get("block_patterns", [])]
        logging.debug(f"[MEDIATOR] Завантажено block_patterns: {patterns}")
        return patterns
    except Exception as e:
        logging.exception(f"[MEDIATOR] Помилка читання {SECURITY_CONFIG_PATH}: {e}")
        return []

def _normalize_cmd(s: str) -> str:
    """
    Уніфікація вводу:
      - схлопнути мультипробіли
      - to lower
      - фінальний слеш привести до ' /'
    """
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    s = s.lower()
    s = re.sub(r"\s*/\s*$", " /", s)
    return s

class Mediator:
    """
    Єдиний вхід ззовні. Рішення просте:
      - trusted → публікуємо у TOPIC_TRUSTED
      - non-trusted → віддаємо на первинну безпеку (SECURITY:IN)
      - blocked commands → публікуємо TOPIC_SECURITY_BLOCK
        (логування про BLOCK робить security.guard)

    SECURITY:IN має обробляти guard (security/guard.py),
    який видає SECURITY:OK/BLOCK/ALERT і, у разі OK, опублікує INBOUND.
    """
    def __init__(self) -> None:
        self._trusted = _load_trusted()
        self._block_patterns = _load_block_patterns()

        # Лінива ініціалізація логерів guard (щоб не замикався імпортний цикл)
        try:
            from security.guard import init_logging as guard_init  # локальний імпорт
            guard_init(log_dir="logs")  # ідемпотентно
        except Exception as e:
            logging.exception("[MEDIATOR] guard_init failed: %s", e)

        logging.debug(f"[MEDIATOR] Ініціалізовано Mediator: trusted={self._trusted}, block_patterns={self._block_patterns}")

    def reload(self) -> None:
        self._trusted = _load_trusted()
        self._block_patterns = _load_block_patterns()
        logging.debug(f"[MEDIATOR] Перезавантажено Mediator: trusted={self._trusted}, block_patterns={self._block_patterns}")

    def is_trusted(self, src: Any) -> bool:
        if src is None:
            logging.debug("[MEDIATOR] Джерело є None, повертаю False")
            return False
        s = str(src)
        is_trusted = s in self._trusted
        logging.debug(f"[MEDIATOR] Перевірка джерела: {s}, is_trusted: {is_trusted}")
        return is_trusted

    def route(self, message: Dict[str, Any]) -> None:
        """
        Старий інтерфейс: залишаємо метод route() для сумісності.
        Очікуємо ключі:
          message['source'] — user/token/ідентифікатор
          message['text']   — команда
        Додатково: якщо ключі лежать у message['payload'], беремо їх звідти.
        """
        logging.debug(f"[MEDIATOR] Отримано повідомлення: {message}")

        # payload fallback — якщо структура інша
        payload = message.get("payload") or {}
        src = message.get("source") or payload.get("source")
        raw_text = message.get("text")
        if raw_text is None:
            raw_text = payload.get("text", "")

        text = _normalize_cmd(raw_text)

        # корисна діагностика структури події
        try:
            logging.debug(
                f"[MEDIATOR] Keys snapshot: top_keys={list(message.keys())}, "
                f"payload_keys={list((payload or {}).keys())}"
            )
        except Exception:
            pass

        logging.debug(
            f"[MEDIATOR] Before guard: src={src!r}, raw_text={raw_text!r}, norm={text!r}, "
            f"trusted_set={self._trusted}, block_patterns={self._block_patterns}"
        )

        # Єдиний центр рішення — guard; саме він пише у security.log / guard.log
        from security.guard import handle_command   # ЛОКАЛЬНИЙ імпорт (розриває цикл)
        verdict = handle_command(text, user=str(src or "unknown"))

        if self.is_trusted(src):
            msg = dict(message)
            msg["source_trusted"] = True
            logging.info(f"MEDIATOR: trusted {src} → TRUSTED")

            if verdict.get("blocked"):
                logging.info(
                    f"MEDIATOR: blocked trusted {src} → SECURITY:BLOCK "
                    f"(command: {text}, reason: {verdict.get('reason')})"
                )
                BUS.publish(TOPIC_SECURITY_BLOCK, {
                    "payload": {
                        "text": text,
                        "reason": verdict.get("reason", "blocked_by_guard"),
                        "source": src
                    }
                })
                logging.debug(f"[MEDIATOR] Опубліковано TOPIC_SECURITY_BLOCK для {text}")
            else:
                logging.debug(f"[MEDIATOR] Команда {text} дозволена для довіреного джерела {src}")
                msg = dict(msg)
                msg["text"] = text  # нормалізований варіант
                BUS.publish(TOPIC_TRUSTED, msg)
                logging.debug(f"[MEDIATOR] Опубліковано TOPIC_TRUSTED для {text}")
        else:
            logging.debug(f"[MEDIATOR] Джерело {src} не є довіреним")
            if verdict.get("blocked"):
                logging.info(
                    f"MEDIATOR: blocked {src} → SECURITY:BLOCK "
                    f"(command: {text}, reason: {verdict.get('reason')})"
                )
                BUS.publish(TOPIC_SECURITY_BLOCK, {
                    "payload": {
                        "text": text,
                        "reason": verdict.get("reason", "blocked_by_guard"),
                        "source": src
                    }
                })
                logging.debug(f"[MEDIATOR] Опубліковано TOPIC_SECURITY_BLOCK для {text}")
            else:
                logging.info(f"MEDIATOR: external {src} → SECURITY:IN")
                msg = dict(message)
                msg["text"] = text  # нормалізований варіант
                BUS.publish("SECURITY:IN", msg)
                logging.debug(f"[MEDIATOR] Опубліковано SECURITY:IN для {text}")

    def handle_inbound(self, message: Dict[str, Any]) -> None:
        logging.debug(f"[MEDIATOR] Викликано handle_inbound з повідомленням: {message}")
        self.route(message)

# Глобальний сінглтон
MEDIATOR = Mediator()
