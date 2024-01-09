from dataclasses import dataclass, field
from typing import Optional, Dict

from .system import System
from .interfaces import Interface


@dataclass
class Device:
    system: Optional[System] = None
    interfaces: Dict[str, Interface] = field(default_factory=dict)
