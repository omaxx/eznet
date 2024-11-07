from __future__ import annotations

import eznet

from .info import Info
from .system import System
from .chassis import Chassis
from .lldp import LLDP
from .interfaces import Interface


class Device:
    def __init__(self, device: eznet.Device):
        self.system = System(device)
        self.chassis = Chassis(device)
        self.lldp = LLDP(device)
        self.interfaces = Info(device, Interface.fetch)
