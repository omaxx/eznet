from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import cattrs

from eznet.utils import list_to_dict

from .bgp import BGP
from .chassis import Chassis
from .interfaces import Interface


@dataclass
class Data:
    chassis: Chassis = None
    interfaces: Dict[str, Interface] = None
    bgp: BGP = None

    @classmethod
    def load(cls, **data) -> Data:
        if 'interfaces' in data:
            data['interfaces'] = list_to_dict(data['interfaces'])
            for interface_name, interface in data['interfaces'].copy().items():
                if 'members' in interface:
                    interface['members'] = list_to_dict(interface['members'])
                    for member_name, member in interface['members'].items():
                        data['interfaces'][member_name] = member
                        data['interfaces'][member_name]['ae'] = interface_name
                        # copy peer.device from interface to member
                        if 'peer' in interface and 'device' in interface['peer']:
                            if 'peer' not in member:
                                member['peer'] = {}
                            if 'device' not in member['peer']:
                                member['peer']['device'] = interface['peer']['device']
                    interface['members'] = [member_name for member_name in interface['members']]

        return cattrs.structure(data, Data)
