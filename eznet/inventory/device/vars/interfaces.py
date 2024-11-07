from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


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
