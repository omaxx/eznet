from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime

from lxml.etree import _Element  # noqa

import eznet
from eznet.data import Data
from eznet.parsers.xml import text, timestamp, number


@dataclass
class Neighbor:
    system_name: str
    chassis_id: str
    port_id: str

    @classmethod
    def from_xml(cls, xml: _Element):
        return cls(
            system_name=text(xml, "lldp-remote-system-name"),
            chassis_id=text(xml, "lldp-remote-chassis-id"),
            port_id=text(xml, "lldp-remote-port-id"),
        )

    @classmethod
    async def fetch(cls, device: eznet.Device) -> Optional[Dict[str, Neighbor]]:
        show_neighbors = await device.junos.run_xml_cmd("show lldp neighbors")
        if show_neighbors is not None:
            neighbors_information = show_neighbors.find("lldp-neighbors-information")
            return {
                port_id: Neighbor.from_xml(e)
                for e in neighbors_information.findall("lldp-neighbor-information")
                if (port_id := text(e, "lldp-local-port-id")) is not None
            }


class LLDP:
    def __init__(self, device: eznet.Device) -> None:
        self.neighbors = Data(device, Neighbor.fetch)
