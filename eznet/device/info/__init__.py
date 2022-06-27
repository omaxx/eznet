from dataclasses import dataclass
from typing import Dict, Union, List

from ..data import Data
from ..drivers import SSH
from .interfaces import AEInterface, Interface, get_interface_info, lb


@dataclass
class Info:
    interfaces: Dict[str, Union[Interface, AEInterface]]

    @classmethod
    def load(cls, ssh: SSH, data: Data):
        return cls(
            interfaces=get_interface_info(ssh, data)
        )

    def interfaces_lb(self, names: List[str]):
        try:
            return {
                "output_bps": lb([
                    self.interfaces[interface_name].traffic_statistics.output_bps
                    for interface_name in names
                ]),
                "output_pps": lb([
                    self.interfaces[interface_name].traffic_statistics.output_pps
                    for interface_name in names
                ]),
            }
        except KeyError:
            return None
