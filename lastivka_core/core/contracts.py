# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

# Теми шини (узгоджені)
TOPIC_SENSOR_ANY = "SENSOR:*"
TOPIC_SENSOR_LIDAR = "SENSOR:LIDAR"
TOPIC_SENSOR_IMU = "SENSOR:IMU"
TOPIC_SENSOR_CAMERA = "SENSOR:CAMERA"

TOPIC_TRUSTED = "TRUSTED"
TOPIC_INBOUND = "INBOUND"
TOPIC_SECURITY_OK = "SECURITY:OK"
TOPIC_SECURITY_BLOCK = "SECURITY:BLOCK"
TOPIC_SECURITY_ALERT = "SECURITY:ALERT"

TOPIC_HEALTH_ANY = "HEALTH:*"
TOPIC_HEALTH_BATTERY = "HEALTH:BATTERY"
TOPIC_HEALTH_TEMP = "HEALTH:TEMP"
TOPIC_HEALTH_IMU = "HEALTH:IMU_SANITY"

class Verdict(str, Enum):
    OK = "OK"
    BLOCK = "BLOCK"
    ALERT = "ALERT"

@dataclass
class SensorEvent:
    type: str                 # "lidar" | "imu" | "camera" | ін.
    ts_ms: int                # timestamp (мс)
    data: Any                 # сирі/оброблені дані сенсора
    meta: Dict[str, Any] = field(default_factory=dict)

@dataclass
class FirewallVerdict:
    verdict: Verdict          # OK | BLOCK | ALERT
    reason: str = ""          # коротке пояснення
    cleaned: Optional[Any] = None  # очищені/нормалізовані дані (за наявності)

@dataclass
class KernelDecision:
    action: str               # "move" | "stop" | "pose" | "recover"
    params: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0

@dataclass
class LocomotionResult:
    status: str               # "applied" | "rejected"
    telemetry: Dict[str, Any] = field(default_factory=dict)
