from typing import Union
from dataclasses import dataclass

from ..drivers import SSH
from ..data import Data

from .interfaces import Interface, AEInterface, get_interface_info


@dataclass
class Info:
    interfaces: dict[str, Union[Interface, AEInterface]]

    @classmethod
    def load(cls, ssh: SSH, data: Data):
        return cls(
            interfaces=get_interface_info(ssh, data)
        )
