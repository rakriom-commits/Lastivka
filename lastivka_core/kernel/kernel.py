# -*- coding: utf-8 -*-
"""
lastivka_core/kernel.py — minimal operational kernel v1.0 (2025-08-18)

Призначення:
- Слухає вхідні події (INBOUND/TRUSTED) з BUS
- Робить примітивні рішення (echo "say") і публікує їх у "KERNEL:DECISION"
- Має елементарний фільтр небезпечних команд і шле SECURITY:* події

Залежності:
- core.event_bus.BUS  (повинен мати .subscribe(topic, cb) та .publish(topic, payload))
- core.contracts (необов’язково; є fallback-рядки для топіків)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.event_bus import BUS
try:
    from core.contracts import (
        TOPIC_INBOUND,
        TOPIC_TRUSTED,
        TOPIC_SECURITY_ALERT,
        TOPIC_SECURITY_BLOCK,
        TOPIC_SECURITY_OK,
    )
except Exception:
    # Fallback-и, якщо core.contracts відсутній
    TOPIC_INBOUND = "INBOUND"
    TOPIC_TRUSTED = "TRUSTED"
    TOPIC_SECURITY_ALERT = "SECURITY:ALERT"
    TOPIC_SECURITY_BLOCK = "SECURITY:BLOCK"
    TOPIC_SECURITY_OK = "SECURITY:OK"

KERNEL_DECISION_TOPIC = "KERNEL:DECISION"

# Дуже грубий фільтр небезпечних команд
_SUSPICIOUS = re.compile(
    r"(rm\s+-rf|format\s+c:|shutdown\s+/s|del\s+/f\s+/q|powershell\s+-enc|curl\s+https?:\/\/.*\|\s*sh)",
    re.IGNORECASE,
)


@dataclass
class Decision:
    action: str
    params: Dict[str, Any]

    def to_event(self) -> Dict[str, Any]:
        return {"decision": {"action": self.action, "params": self.params}}


class Kernel:
    def __init__(self, *, bus=BUS, logger: Optional[logging.Logger] = None) -> None:
        self.bus = bus
        self.log = logger or logging.getLogger("Kernel")
        self.log.info("[Kernel] init")

        # Підписки на вхідні повідомлення (довірені/загальні)
        self.bus.subscribe(TOPIC_INBOUND, self._on_inbound)
        self.bus.subscribe(TOPIC_TRUSTED, self._on_inbound)

        # Сигнал готовності
        self.bus.publish(KERNEL_DECISION_TOPIC, Decision("ready", {}).to_event())

    def start(self) -> None:
        """Поки що фонового циклу немає — запуск no-op."""
        self.log.info("[Kernel] start (noop)")

    # ---- Внутрішні обробники ----

    def _on_inbound(self, evt: Dict[str, Any]) -> None:
        """Основний хендлер вхідних подій від BUS."""
        try:
            payload = evt.get("payload") or {}
            text = (payload.get("text") or payload.get("message") or "").strip()
            source = payload.get("source", "unknown")

            if not text:
                return

            # Примітивна безпека
            if _SUSPICIOUS.search(text):
                self.bus.publish(
                    TOPIC_SECURITY_BLOCK,
                    {"reason": f"заблоковано підозрілу команду від {source}"},
                )
                return

            # Базове рішення — сказати те, що прийшло (echo)
            decision = Decision("say", {"text": text})
            self.bus.publish(KERNEL_DECISION_TOPIC, decision.to_event())

            # Пінг безпеці, що все ок
            self.bus.publish(TOPIC_SECURITY_OK, {"source": source})

        except Exception as e:
            self.log.exception("Kernel inbound error: %s", e)
            self.bus.publish(
                TOPIC_SECURITY_ALERT,
                {"reason": "Kernel inbound exception", "error": str(e)},
            )
