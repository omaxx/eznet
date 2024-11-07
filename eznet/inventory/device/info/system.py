from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from xml.etree.ElementTree import Element

import eznet
from eznet.parsers.xml import text, timestamp

from .info import Info, raise_error


@dataclass
class SysInfo:
    hostname: Optional[str]
    sw_family: Optional[str]
    sw_version: Optional[str]
    hw_model: Optional[str]
    hw_sn: Optional[str]

    @staticmethod
    def from_xml(system_info: Element) -> SysInfo:
        return SysInfo(
            hostname=text(system_info, "host-name"),
            sw_family=text(system_info, "os-name"),
            sw_version=text(system_info, "os-version"),
            hw_model=text(system_info, "hardware-model"),
            hw_sn=text(system_info, "serial-number"),
        )

    @staticmethod
    async def fetch(device: eznet.Device) -> SysInfo:
        xml = await device.run_xml_cmd(
            "show system information",
        )
        if (system_info := xml.find("system-information")) is not None:
            return SysInfo.from_xml(system_info)
        else:
            return raise_error(xml)


@dataclass
class Alarm:
    ts: Optional[datetime]
    cls: Optional[str]
    description: Optional[str]
    type: Optional[str]

    @staticmethod
    def from_xml(alarm: Element) -> Alarm:
        return Alarm(
            ts=timestamp(alarm, "alarm-time"),
            cls=text(alarm, "alarm-class"),
            description=text(alarm, "alarm-description"),
            type=text(alarm, "alarm-type"),
        )

    @staticmethod
    async def fetch(device: eznet.Device) -> list[Alarm]:
        xml = await device.run_xml_cmd(
            "show system alarms",
        )
        if (alarm_info := xml.find("alarm-information")) is not None:
            return [
                Alarm.from_xml(alarm) for alarm in alarm_info.findall("alarm-detail")
            ]
        else:
            return raise_error(xml)


@dataclass
class SW:
    hostname: Optional[str]
    product_model: Optional[str]
    product_name: Optional[str]
    junos: Optional[str]

    @staticmethod
    def from_xml(soft_info: Element) -> SW:
        return SW(
            hostname=text(soft_info, "host-name"),
            product_model=text(soft_info, "product-model"),
            product_name=text(soft_info, "product-name"),
            junos=text(soft_info, "junos-version"),
        )

    @staticmethod
    async def fetch(device: eznet.Device, both_re: bool = False) -> dict[str, SW]:
        if not both_re:
            xml = await device.run_xml_cmd(
                "show version",
            )
        else:
            xml = await device.run_xml_cmd(
                "show version invoke-on all-routing-engines",
            )

        if (soft_info := xml.find("software-information")) is not None:
            return {"localre": SW.from_xml(soft_info)}
        elif (mre_results := xml.find("multi-routing-engine-results")) is not None:
            return {
                re_name: SW.from_xml(sw_info)
                for mre_item in mre_results.findall("multi-routing-engine-item")
                if (re_name := text(mre_item, "re-name")) is not None
                and (sw_info := mre_item.find("software-information")) is not None
            }
        else:
            return raise_error(xml)


class System:
    def __init__(self, device: eznet.Device):
        self.info = Info(device, SysInfo.fetch)
        self.alarm = Info(device, Alarm.fetch)
        self.sw = Info(device, SW.fetch)
