from __future__ import annotations


from typing import Optional, Dict

from attrs import define

from .system import System
from .interfaces import Interface


@define
class Device:
    system: Optional[System] = None
    interfaces: Optional[Dict[str, Interface]] = None
