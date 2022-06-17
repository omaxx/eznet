from dataclasses import dataclass, field
from typing import Dict


@dataclass
class XCVR:
    pass


@dataclass
class PIC:
    xcvr: Dict[int, XCVR] = field(default_factory=dict)


@dataclass
class FPC:
    pic: Dict[int, PIC] = field(default_factory=dict)


@dataclass
class Chassis:
    fpc: Dict[int, FPC] = field(default_factory=dict)
