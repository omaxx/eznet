from __future__ import annotations

import eznet

from .system import System


class Device:
    def __init__(self, device: eznet.Device):
        self.system = System(device)
