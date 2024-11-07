from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from xml.etree.ElementTree import Element
from lxml.etree import _Element

import eznet
from eznet.parsers.xml import text, timestamp, number

from .info import Info, raise_error


@dataclass
class Neighbor:
    system_name: Optional[str]
    chassis_id: Optional[str]
    port_id: Optional[str]

    @classmethod
    def from_xml(cls, xml: Element) -> Neighbor:
        return cls(
            system_name=text(xml, "lldp-remote-system-name"),
            chassis_id=text(xml, "lldp-remote-chassis-id"),
            port_id=text(xml, "lldp-remote-port-id"),
        )

    @classmethod
    async def fetch(cls, device: eznet.Device) -> dict[str, Neighbor]:
        show_neighbors = await device.run_xml_cmd("show lldp neighbors")
        if (neighbors_information := show_neighbors.find("lldp-neighbors-information")) is not None:
            return {
                port_id: Neighbor.from_xml(e)
                for e in neighbors_information.findall("lldp-neighbor-information")
                if (port_id := text(e, "lldp-local-port-id")) is not None
            }
        else:
            raise_error(show_neighbors)


class LLDP:
    def __init__(self, device: eznet.Device) -> None:
        self.neighbors = Info(device, Neighbor.fetch)
