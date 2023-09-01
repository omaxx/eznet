from __future__ import annotations

import eznet
from eznet.data import Data


from .system import System
from .chassis import Chassis
from .interfaces import Interface


class Device:
    def __init__(self, device: eznet.device.Device):
        self.system = System(device)
        self.chassis = Chassis(device)
        self.interfaces = Data(Interface.fetch, device)
