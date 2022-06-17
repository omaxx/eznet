from dataclasses import dataclass, field


@dataclass
class XCVR:
    pass


@dataclass
class PIC:
    xcvr: dict[int, XCVR] = field(default_factory=dict)


@dataclass
class FPC:
    pic: dict[int, PIC] = field(default_factory=dict)


@dataclass
class Chassis:
    fpc: dict[int, FPC] = field(default_factory=dict)
