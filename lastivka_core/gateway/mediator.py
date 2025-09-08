# gateway/mediator.py (patched: BASE_DIR config lookup + flat SECURITY_BLOCK payload)
from __future__ import annotations

import re, json, logging
from pathlib import Path
from core.event_bus import BUS
from core.contracts import TOPIC_INBOUND, TOPIC_TRUSTED, TOPIC_SECURITY_BLOCK

BASE_DIR = Path(__file__).resolve().parents[1]  # ...\lastivka_core

def _load_yaml_or_json(p: Path):
    if not p.exists():
        logging.warning("[MEDIATOR] Конфігурація %s не знайдена, використовую дефолти", p)
        return {}
    if p.suffix.lower() in (".yml", ".yaml"):
        import yaml
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return json.loads(p.read_text(encoding="utf-8"))

class Mediator:
    def __init__(self, bus=BUS):
        self.bus = bus
        sys_cfg  = _load_yaml_or_json(BASE_DIR / "config" / "system" / "config.yaml")
        root_cfg = _load_yaml_or_json(BASE_DIR / "config" / "config.yaml")

        self.whitelist = set((sys_cfg.get("whitelist") or {}).get("users", []))
        self.block_patterns = [re.compile(p, re.I) for p in (root_cfg.get("block_patterns") or [])]

        self.bus.subscribe("input", self.handle_inbound)
        logging.debug("[MEDIATOR] Ініціалізовано Mediator: trusted=%s, block_patterns=%s",
                      self.whitelist, [p.pattern for p in self.block_patterns])

    def handle_inbound(self, evt):
        payload = (evt or {}).get("payload") or {}
        text = (payload.get("text") or "").strip()
        src  = payload.get("source", "unknown")

        # Блок небезпечних шаблонів → SECURITY_BLOCK з плоским payload
        if any(p.search(text) for p in self.block_patterns):
            self.bus.publish(TOPIC_SECURITY_BLOCK, {"text": text, "reason": "blocked by pattern", "source": src})
            return

        # Whitelist користувачів → TRUSTED, решта → INBOUND
        if src in self.whitelist:
            self.bus.publish(TOPIC_TRUSTED, {"text": text, "source": src})
        else:
            self.bus.publish(TOPIC_INBOUND, {"text": text, "source": src})

# Сінглтон
MEDIATOR = Mediator()
