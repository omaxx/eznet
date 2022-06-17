from dataclasses import dataclass, field


@dataclass
class Peer:
    pass


@dataclass
class Group:
    peers: dict[str, Peer] = field(default_factory=dict)


@dataclass
class BGP:
    groups: dict[str, Group] = field(default_factory=dict)