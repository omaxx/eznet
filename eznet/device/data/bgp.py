from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Peer:
    pass


@dataclass
class Group:
    peers: Dict[str, Peer] = field(default_factory=dict)


@dataclass
class BGP:
    groups: Dict[str, Group] = field(default_factory=dict)