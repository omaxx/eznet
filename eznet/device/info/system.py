from __future__ import annotations

from typing import Optional, Dict, List
from datetime import datetime

from attrs import define
from lxml.etree import _Element  # noqa

import eznet
from eznet.parser.xml import text, timestamp, number
from eznet.data import Data


@define
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
    async def fetch(device: eznet.device.Device) -> Optional[Info]:
        xml = await device.junos.run_xml_cmd(
            "show system information",
        )
        if xml is not None:
            system_info = xml.find("system-information")
            if system_info is not None:
                return Info.from_xml(system_info)
        return None


@define
class SW:
    hostname: Optional[str]
    product_model: Optional[str]
    product_name: Optional[str]
    junos: Optional[str]

    @staticmethod
    def from_xml(soft_info: _Element) -> SW:
        return SW(
            hostname=text(soft_info, "host-name"),
            product_model=text(soft_info, "product-model"),
            product_name=text(soft_info, "product-name"),
            junos=text(soft_info, "junos-version"),
        )

    @staticmethod
    async def fetch(device: eznet.device.Device, both_re: bool = False) -> Optional[Dict[str, SW]]:
        if not both_re:
            xml = await device.junos.run_xml_cmd(
                "show version",
            )
        else:
            xml = await device.junos.run_xml_cmd(
                "show version invoke-on all-routing-engines",
            )

        if xml is not None:
            soft_info = xml.find("software-information")
            if soft_info is not None:
                return {
                    "localre": SW.from_xml(soft_info)
                }
            mre_results = xml.find("multi-routing-engine-results")
            if mre_results is not None:
                return {
                    text(mre_item, "re-name"):
                        SW.from_xml(mre_item.find("software-information"))
                    for mre_item in mre_results.findall("multi-routing-engine-item")
                    if text(mre_item, "re-name") is not None
                    and mre_item.find("software-information") is not None
                }
        return None


@define
class Uptime:
    current_time: Optional[datetime]
    system_boot_time: Optional[datetime]
    protocol_start_time: Optional[datetime]
    last_config_time: Optional[datetime]
    time_source: Optional[str]

    @staticmethod
    def from_xml(uptime_info: _Element) -> Uptime:
        return Uptime(
            current_time=timestamp(uptime_info, "current-time/date-time"),
            system_boot_time=timestamp(uptime_info, "system-booted-time/date-time"),
            protocol_start_time=timestamp(uptime_info, "protocols-started-time/date-time"),
            last_config_time=timestamp(uptime_info, "last-configured-time/date-time"),
            time_source=text(uptime_info, "time-source", strip=True),
        )

    @staticmethod
    async def fetch(device: eznet.device.Device, both_re: bool = False) -> Optional[Dict[str, Uptime]]:
        if not both_re:
            xml = await device.junos.run_xml_cmd("show system uptime")
        else:
            xml = await device.junos.run_xml_cmd("show system uptime invoke-on all-routing-engines")
        if xml is not None:
            system_uptime = xml.find("system-uptime-information")
            if system_uptime is not None:
                return {
                    "localre": Uptime.from_xml(system_uptime)
                }
            mre_results = xml.find("multi-routing-engine-results")
            if mre_results is not None:
                return {
                    text(mre_item, "re-name"):
                        Uptime.from_xml(mre_item.find("system-uptime-information"))
                    for mre_item in mre_results.findall("multi-routing-engine-item")
                    if text(mre_item, "re-name") is not None
                    and mre_item.find("system-uptime-information") is not None
                }
        return None


@define
class CoreDump:
    name: Optional[str]
    size: Optional[int]
    ts: Optional[datetime]
    re: Optional[str] = None
    host: Optional[bool] = None

    @staticmethod
    def from_xml(file_info: _Element) -> CoreDump:
        return CoreDump(
            name=text(file_info, "file-name"),
            size=number(file_info, "file-size"),
            ts=timestamp(file_info, "file-date"),
            re=text(file_info, "../../../re-name"),
            host=file_info.find("../..").attrib.get("style") == "host" or None,
        )

    @staticmethod
    async def fetch(device: eznet.device.Device, both_re: bool = False) -> Optional[List[CoreDump]]:
        if not both_re:
            xml = await device.junos.run_xml_cmd(
                "show system core-dumps",
            )
        else:
            xml = await device.junos.run_xml_cmd(
                "show system core-dumps routing-engine both",
            )
        if xml is not None:
            return [
                CoreDump.from_xml(file_info)
                for file_info in xml.findall(".//directory-list/directory/file-information")
            ]
        return None


@define
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
    async def fetch(device: eznet.device.Device) -> Optional[List[Alarm]]:
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


class System:
    def __init__(self, device: eznet.device.Device):
        self.info = Data(Info.fetch, device)
        self.sw = Data(SW.fetch, device)
        self.uptime = Data(Uptime.fetch, device)
        self.coredumps = Data(CoreDump.fetch, device)
        self.alarms = Data(Alarm.fetch, device)
        