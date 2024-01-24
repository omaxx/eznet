from __future__ import annotations

from dataclasses import dataclass, field

import eznet

from .system import System
from .chassis import Chassis


class Device:
    def __init__(self, device: eznet.Device) -> None:
        self.system = System(device)
        self.chassis = Chassis(device)
