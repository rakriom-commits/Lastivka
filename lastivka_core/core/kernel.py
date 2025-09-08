# lastivka_core/kernel.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict
from pathlib import Path
import yaml
import logging
from core.event_bus import BUS
from core.contracts import (
    TOPIC_TRUSTED, TOPIC_INBOUND, TOPIC_SECURITY_ALERT,
    TOPIC_SECURITY_BLOCK, TOPIC_SENSOR_ANY, KernelDecision, LocomotionResult
)
CONFIG_PATH = Path("config/config.yaml")

# Налаштування логера для security.log
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("C:/Lastivka/lastivka_core/logs/security.log", encoding="utf-8")
    ]
)
security_logger = logging.getLogger("security")

def _load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    # дефолти, якщо файл ще не злитий у єдиний
    return {
        "limits": {"vx_max": 0.5, "vy_max": 0.3, "yaw_rate_max": 0.5},
        "profiles": {"move_slow": {"vx": 0.2, "vy": 0.0, "yaw": 0.0}},
        "whitelist": {"users": ["Олег", "Софія"], "tokens": []}
    }

class Kernel:
    """
    Мінімальне ядро: підписки на події, простий приймач рішень.
    Ні RL, ні складних стратегій — лише каркас і безпечні дефолти.
    """
    def __init__(self) -> None:
        self.cfg = _load_config()
        BUS.subscribe(TOPIC_TRUSTED, self.on_trusted)
        BUS.subscribe(TOPIC_INBOUND, self.on_inbound_ok)
        BUS.subscribe(TOPIC_SECURITY_ALERT, self.on_alert)
        BUS.subscribe(TOPIC_SECURITY_BLOCK, self.on_block)  # Додано підписку на блокування
        BUS.subscribe(TOPIC_SENSOR_ANY, self.on_sensor)

    # === Handlers ===
    def on_trusted(self, evt: Dict[str, Any]) -> None:
        # Довірені команди (Олег/Софія/білий список)
        payload = evt["payload"]
        cmd = str(payload.get("text", "")).lower()
        if "move" in cmd:
            dec = self._decide_move_slow()
        elif "stop" in cmd or "стоп" in cmd:
            dec = KernelDecision(action="stop")
        else:
            dec = KernelDecision(action="stop")  # дефолт безпечний
        self._apply(dec)

    def on_inbound_ok(self, evt: Dict[str, Any]) -> None:
        # Зовнішні санкціоновані (після guard) → дуже обережно
        self._apply(KernelDecision(action="stop"))

    def on_alert(self, evt: Dict[str, Any]) -> None:
        # Будь-яка серйозна загроза → безпечна зупинка
        self._apply(KernelDecision(action="stop", priority=10))

    def on_block(self, evt: Dict[str, Any]) -> None:
        # Обробка блокувань (наприклад, rm -rf /)
        payload = evt.get("payload", {})
        command = payload.get("text", "невідома команда")
        reason = payload.get("reason", "невідома причина")
        security_logger.info(f"[INPUT] {command} → Verdict: BLOCK | Reason: {reason}")

    def on_sensor(self, evt: Dict[str, Any]) -> None:
        # Поки лише «тримай позицію»; політика з’явиться на Етапі 3
        # Можна додати прості реакції на батарею/нахил у майбутньому
        pass

    # === Decisions ===
    def _decide_move_slow(self) -> KernelDecision:
        prof = (self.cfg.get("profiles") or {}).get("move_slow", {})
        return KernelDecision(action="move", params={
            "vx": float(prof.get("vx", 0.2)),
            "vy": float(prof.get("vy", 0.0)),
            "yaw": float(prof.get("yaw", 0.0)),
        }, priority=1)

    # === Effects (execution bridge) ===
    def _apply(self, decision: KernelDecision) -> LocomotionResult:
        """
        Тут поки що лише публікуємо рішення для виконання модулем руху.
        Реальний виконавець читає тему 'KERNEL:DECISION' і діє.
        """
        BUS.publish("KERNEL:DECISION", {
            "decision": {
                "action": decision.action,
                "params": decision.params,
                "priority": decision.priority
            }
        })
        return LocomotionResult(status="applied", telemetry={})