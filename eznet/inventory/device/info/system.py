from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from lxml.etree import _Element  # noqa

import eznet
from eznet.parsers.xml import text


@dataclass
class Info:
    hostname: Optional[str]
    sw_family: Optional[str]
    sw_version: Optional[str]
    hw_model: Optional[str]
    hw_sn: Optional[str]

    @staticmethod
    def from_xml(system_info: _Element) -> Info:
        return Info(
            hostname=text(system_info, "host-name"),
            sw_family=text(system_info, "os-name"),
            sw_version=text(system_info, "os-version"),
            hw_model=text(system_info, "hardware-model"),
            hw_sn=text(system_info, "serial-number"),
        )

    @staticmethod
    async def fetch(device: eznet.Device) -> Optional[Info]:
        xml = await device.junos.run_xml_cmd(
            "show system information",
        )
        if xml is not None:
            system_info = xml.find("system-information")
            if system_info is not None:
                return Info.from_xml(system_info)
        return None


class System:
    def __init__(self) -> None:
        self.info: list[Info] = []
