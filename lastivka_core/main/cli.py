# -*- coding: utf-8 -*-
from __future__ import annotations
from core.event_bus import EventBus
from lastivka_core.kernel import Kernel
from gateway.mediator import Mediator

if __name__ == "__main__":
    bus = EventBus()
    _kernel = Kernel(bus)
    _mediator = Mediator(bus)
    print("Lastivka: Stage 0 skeleton OK")
