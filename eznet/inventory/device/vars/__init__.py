from dataclasses import dataclass, field
from typing import Dict, Optional

from .interfaces import Interface
from .system import System


@dataclass
class Device:
    system: Optional[System] = None
    interfaces: Dict[str, Interface] = field(default_factory=dict)
