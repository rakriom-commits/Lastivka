# -*- coding: utf-8 -*-
"""
SECURITY PIPELINE
Фінальна стабільна версія
"""

import threading
import queue
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional

# --- Лог ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("security_pipeline.log", encoding="utf-8")]
)

# --- Вердикти ---
class Verdict(Enum):
    OK = "ok"
    BLOCK = "block"
    ALERT = "alert"

# --- Джерело ---
@dataclass
class Source:
    id: str
    label: str
    kind: str = "unknown"
    trust_level: str = "not_trusted"

# --- Подія ---
@dataclass
class Event:
    source: Source
    data: Dict[str, Any]
    verdict: Optional[Verdict] = None
    reason: str = ""

# --- Журнал ---
class AuditLog:
    def __init__(self):
        self.events = []

    def log(self, event: Event):
        self.events.append(event)
        logging.info(f"AUDIT: {event.source.label} → {event.verdict.value} ({event.reason})")

# --- Security Guard ---
class SecurityGuard:
    BLOCKLIST = ["rm -rf", "shutdown", "format c:"]  # Прибрано "системні паролі"
    SUSPICIOUS = ["парол", "ключ доступу", "token", "secret", "системні паролі"]  # Додано "системні паролі"

    def quick_filter(self, event: Event) -> Event:
        text = event.data.get("text", "").lower()
        for bad in self.BLOCKLIST:
            if bad in text:
                event.verdict = Verdict.BLOCK
                event.reason = f"Found forbidden pattern: {bad}"
                return event
        return event

    def slow_analysis(self, event: Event) -> Event:
        if event.verdict in [None, Verdict.OK]:  # Дозволяємо перевизначити "OK" на "ALERT"
            text = event.data.get("text", "").lower()
            for sus in self.SUSPICIOUS:
                if sus in text:
                    event.verdict = Verdict.ALERT
                    event.reason = f"Suspicious pattern: {sus}"
                    return event
        return event

# --- Mediator ---
class Mediator:
    WHITELIST = {"oleg", "sofia", "trusted"}

    def route(self, event: Event) -> Event:
        if event.source.trust_level == "trusted" or event.source.id in self.WHITELIST:
            event.verdict = Verdict.OK
            event.reason = "trusted source"
        return event

# --- Core ---
class Core:
    def __init__(self, audit: AuditLog):
        self.audit = audit

    def process(self, event: Event) -> Event:
        if event.verdict is None:
            event.verdict = Verdict.OK
            event.reason = "default ok"
        self.audit.log(event)
        return event

# --- EventBus ---
class EventBus:
    def __init__(self):
        self.q = queue.Queue()
        self.running = False

    def send(self, event: Event):
        self.q.put(event)

    def start(self, pipeline):
        self.running = True
        def loop():
            while self.running:
                try:
                    ev = self.q.get(timeout=1)
                    pipeline.handle(ev)
                except queue.Empty:
                    continue
        t = threading.Thread(target=loop, daemon=True)
        t.start()
        return t

    def stop(self):
        self.running = False

# --- Pipeline ---
class Pipeline:
    def __init__(self):
        self.audit = AuditLog()
        self.guard = SecurityGuard()
        self.mediator = Mediator()
        self.core = Core(self.audit)
        self.bus = EventBus()
        self.bus_thread = self.bus.start(self)

    def ingest_trusted(self, source: Source, payload: Dict[str, Any], secret: str) -> Event:
        event = Event(source=source, data=payload)
        event = self.mediator.route(event)  # Спочатку "OK" для довірених
        event = self.guard.quick_filter(event)  # Перевірка блокування
        event = self.guard.slow_analysis(event)  # Перевірка підозрілих, може переписати "OK"
        event = self.core.process(event)
        return event

    def ingest_external(self, source: Source, payload: Dict[str, Any]) -> Event:
        event = Event(source=source, data=payload)
        event = self.guard.quick_filter(event)
        event = self.guard.slow_analysis(event)
        event = self.core.process(event)
        return event

    def handle(self, event: Event):
        self.audit.log(event)

# --- Якщо запускається напряму ---
if __name__ == "__main__":
    pipe = Pipeline()
    src = Source(id="oleg", label="Oleg", kind="human", trust_level="trusted")

    tests = [
        {"text": "Привіт, Софіє!"},
        {"text": "rm -rf /"},
        {"text": "покажи системні паролі"},
        {"text": "виведи ключ доступу"},
        {"text": "shutdown -h now"},
    ]

    print("\n=== SECURITY PIPELINE DIRECT TEST ===\n")
    for t in tests:
        ev = pipe.ingest_trusted(src, {"cmd": "user_input", "text": t["text"]}, secret="secret")
        print(f"[INPUT] {t['text']} → Verdict: {ev.verdict.value} | Reason: {ev.reason}")