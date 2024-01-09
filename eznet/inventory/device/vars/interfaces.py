from __future__ import annotations

from typing import Optional, Dict
from dataclasses import dataclass, field


@dataclass
class Peer:
    device: Optional[str] = None
    interface: Optional[str] = None


@dataclass
class Member:
    peer: Optional[Peer] = None


@dataclass
class Interface:
    members: Dict[str, Member] = field(default_factory=dict)
    peer: Optional[Peer] = None
