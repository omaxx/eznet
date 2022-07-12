from dataclasses import dataclass
from typing import Dict, Union, List

from ..data import Data
from ..drivers import SSH
from .interfaces import Interface, get_interfaces_info, lb


@dataclass
class Info:
    interfaces: Dict[str, Interface]

    @classmethod
    def load(cls, ssh: SSH, data: Data):
        interfaces_info = get_interfaces_info(ssh)
        return cls(
            interfaces=interfaces_info
        )
