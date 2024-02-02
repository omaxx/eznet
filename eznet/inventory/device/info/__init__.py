from __future__ import annotations

from dataclasses import dataclass, field

import eznet
from eznet.data import Data

from .system import System
from .chassis import Chassis
from .lldp import LLDP
from .interfaces import Interface


class Device:
    def __init__(self, device: eznet.Device) -> None:
        self.system = System(device)
        self.chassis = Chassis(device)
        self.lldp = LLDP(device)

        self.interfaces = Data(device, Interface.fetch)
