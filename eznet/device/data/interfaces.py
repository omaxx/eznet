from dataclasses import dataclass
from typing import List


@dataclass
class Peer:
    device: str = None
    interface: str = None


@dataclass
class XCVR:
    speed: str = None
    type: str = None


@dataclass
class Interface:
    members: List[str] = None
    peer: Peer = None
    xcvr: XCVR = None
    ae: str = None
