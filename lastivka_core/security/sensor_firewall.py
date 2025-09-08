# -*- coding: utf-8 -*-
class SensorFirewall:
    def is_weird(self, message: dict) -> bool:
        # поки що лише тестовий прапор
        return bool(message.get("force_weird", False))
