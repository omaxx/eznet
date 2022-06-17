from dataclasses import dataclass
from typing import Dict, Union

from ..data import Data
from ..drivers import SSH
from .interfaces import AEInterface, Interface, get_interface_info


@dataclass
class Info:
    interfaces: Dict[str, Union[Interface, AEInterface]]

    @classmethod
    def load(cls, ssh: SSH, data: Data):
        return cls(
            interfaces=get_interface_info(ssh, data)
        )
