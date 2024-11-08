from __future__ import annotations

import eznet

from .chassis import Chassis
from .info import Info
from .interfaces import Interface
from .lldp import LLDP
from .system import System


class Device:
    def __init__(self, device: eznet.Device):
        self.system = System(device)
        self.chassis = Chassis(device)
        self.lldp = LLDP(device)
        self.interfaces = Info(device, Interface.fetch)
