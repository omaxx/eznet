from dataclasses import dataclass
from typing import Dict


@dataclass
class Member:
    pass


@dataclass
class Interface:
    members: Dict[str, Member] = None
