from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

from lxml.etree import _Element  # noqa

import eznet
from eznet.data import Data
from eznet.parsers.xml import text, timestamp


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


@dataclass
class Alarm:
    ts: Optional[datetime]
    cls: Optional[str]
    description: Optional[str]
    type: Optional[str]

    @staticmethod
    def from_xml(alarm: _Element) -> Alarm:
        return Alarm(
            ts=timestamp(alarm, "alarm-time"),
            cls=text(alarm, "alarm-class"),
            description=text(alarm, "alarm-description"),
            type=text(alarm, "alarm-type"),
        )

    @staticmethod
    async def fetch(device: eznet.Device) -> Optional[List[Alarm]]:
        xml = await device.junos.run_xml_cmd(
            "show system alarms",
        )
        if xml is not None:
            alarm_info = xml.find("alarm-information")
            if alarm_info is not None:
                return [
                    Alarm.from_xml(alarm)
                    for alarm in alarm_info.findall("alarm-detail")
                ]
        return None


class System:
    def __init__(self, device: eznet.Device) -> None:
        self.info = Data(Info.fetch, device)
        self.alarms = Data(Alarm.fetch, device)
