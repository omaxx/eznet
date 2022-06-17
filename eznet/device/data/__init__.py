from __future__ import annotations

from dataclasses import dataclass

import cattrs

from eznet.utils import list_to_dict

from .bgp import BGP
from .chassis import Chassis
from .interfaces import Interface


@dataclass
class Data:
    chassis: Chassis = None
    interfaces: dict[str, Interface] = None
    bgp: BGP = None

    @classmethod
    def load(cls, **data) -> Data:
        if 'interfaces' in data:
            data['interfaces'] = list_to_dict(data['interfaces'])
            for interface in data['interfaces'].values():
                if 'members' in interface:
                    interface['members'] = list_to_dict(interface['members'])

        return cattrs.structure(data, Data)
