# core/event_bus.py
# -*- coding: utf-8 -*-
import logging
from typing import Callable, Dict, List, Any
from fnmatch import fnmatch

EventHandler = Callable[[dict], None]

class EventBus:
    """Проста шина подій з підтримкою вайлдкарт тем (наприклад, 'SENSOR:*')."""
    def __init__(self) -> None:
        self._subs: Dict[str, List[EventHandler]] = {}

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Підписка на точну тему або шаблон з * (напр. 'SENSOR:*')."""
        self._subs.setdefault(topic, []).append(handler)

    def unsubscribe(self, topic: str, handler: EventHandler) -> None:
        handlers = self._subs.get(topic)
        if not handlers:
            return
        try:
            handlers.remove(handler)
        except ValueError:
            pass
        if not handlers:
            self._subs.pop(topic, None)

    def publish(self, topic: str, payload: Dict[str, Any]) -> None:
        """
        Публікує подію у вигляді {'topic': topic, 'payload': payload}
        Викликає обробники як для точного співпадіння теми, так і для шаблонів.
        """
        evt = {"topic": topic, "payload": payload}

        # 1) Точні збіги
        for h in list(self._subs.get(topic, [])):
            try:
                h(evt)
            except Exception:
                logging.exception(f"Handler failed for topic={topic} (exact)")

        # 2) Вайлдкарти (напр. 'SENSOR:*', 'HEALTH:*', тощо)
        for patt, handlers in list(self._subs.items()):
            if "*" in patt and fnmatch(topic, patt):
                for h in list(handlers):
                    try:
                        h(evt)
                    except Exception:
                        logging.exception(f"Handler failed for topic={topic} via pattern={patt}")

# Глобальний сінглтон шини
BUS = EventBus()
