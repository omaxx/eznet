from dataclasses import dataclass
from typing import Optional


@dataclass
class System:
    hostname: Optional[str] = None
