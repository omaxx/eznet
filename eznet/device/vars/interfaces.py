from __future__ import annotations

from typing import Optional, Dict

from attrs import define


@define
class Peer:
    device: Optional[str] = None
    interface: Optional[str] = None


@define
class Member:
    peer: Optional[Peer] = None


@define
class Interface:
    members: Optional[Dict[str, Member]] = None
    peer: Optional[Peer] = None
