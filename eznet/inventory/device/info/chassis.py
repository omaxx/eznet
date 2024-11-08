from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from xml.etree.ElementTree import Element

from lxml.etree import _Element

import eznet
from eznet.parsers.xml import number, text, timestamp

from .info import Info, raise_error


@dataclass
class RE:
    model: Optional[str]
    status: Optional[str]
    mastership: Optional[str]
    start_time: Optional[datetime]
    reboot_reason: Optional[str]

    @staticmethod
    def from_xml(xml: Element) -> RE:
        return RE(
            model=text(xml, "model"),
            status=text(xml, "status"),
            mastership=text(xml, "mastership-state"),
            start_time=timestamp(xml, "start-time"),
            reboot_reason=text(xml, "last-reboot-reason"),
        )

    @staticmethod
    async def fetch(device: eznet.Device) -> dict[int, RE]:
        xml = await device.run_xml_cmd("show chassis routing-engine")
        if (re_information := xml.find("route-engine-information")) is not None:
            return {
                slot: RE.from_xml(e)
                for e in re_information.findall("route-engine")
                if (slot := number(e, "slot")) is not None
            }
        else:
            raise_error(xml)


@dataclass
class Port:
    cable_type: Optional[str]
    fiber_mode: Optional[str]
    wavelength: Optional[str]

    @staticmethod
    def from_xml(port: Element) -> Port:
        return Port(
            cable_type=text(port, "cable-type"),
            fiber_mode=text(port, "fiber-mode"),
            wavelength=text(port, "wavelength"),
        )

@dataclass
class PIC:
    state: Optional[str]
    type: Optional[str]
    ports: Optional[dict[int, Port]] = None

    @staticmethod
    def from_xml(pic: Element) -> PIC:
        return PIC(
            state=text(pic, "pic-state"),
            type=text(pic, "pic-type"),
        )


@dataclass
class FPC:
    state: Optional[str]
    comment: Optional[str]
    cpu_utilization_total: Optional[int]
    cpu_utilization_interrupt: Optional[int]
    memory_dram: Optional[int]
    memory_heap_utilization: Optional[int]
    memory_buffer_utilization: Optional[int]
    description: Optional[str]
    pics: dict[int, PIC]

    @staticmethod
    def from_xml(fpc: Element) -> FPC:
        return FPC(
            state=text(fpc, "state"),
            comment=text(fpc, "comment"),
            cpu_utilization_total=number(fpc, "cpu-total"),
            cpu_utilization_interrupt=number(fpc, "cpu-interrupt"),
            memory_dram=number(fpc, "memory-dram-size"),
            memory_heap_utilization=number(fpc, "memory-heap-utilization"),
            memory_buffer_utilization=number(fpc, "memory-buffer-utilization"),
            description=text(fpc, "description"),
            pics={
                pic_slot: PIC.from_xml(pic)
                for pic in fpc.findall("pic")
                if (pic_slot := number(pic, "pic-slot")) is not None
            },
        )

    @staticmethod
    async def fetch(device: eznet.Device, get_ports: bool = False) -> dict[int, FPC]:
        show_chassis_fpc = await device.run_xml_cmd("show chassis fpc pic-status")
        if (fpc_info := show_chassis_fpc.find("fpc-information")) is not None:
            fpc_dict = {
                fpc_slot: FPC.from_xml(fpc)
                for fpc in fpc_info.findall("fpc")
                if (fpc_slot := number(fpc, "slot")) is not None
            }

            if not get_ports:
                return fpc_dict
            else:
                for fpc_number, fpc in fpc_dict.items():
                    for pic_number, pic in fpc.pics.items():
                        xml = await device.run_xml_cmd(
                            f"show chassis pic fpc-slot {fpc_number} pic-slot {pic_number}",
                        )
                        pic.ports = {
                            port_number: Port.from_xml(port)
                            for port in xml.findall("fpc-information/fpc/pic-detail/port-information/port")
                            if (port_number := number(port, "port-number")) is not None
                        }
                return fpc_dict
        else:
            raise_error(show_chassis_fpc)


@dataclass
class FW:
    fw: dict[str, str]

    @staticmethod
    def from_xml(xml: Element) -> FW:
        fw = {
            fw_type: text(e, "firmware-version")
            for e in xml.findall("firmware")
            if (fw_type := text(e, "type")) is not None
        }
        if "ONIE/DIAG" in fw and (onie_diag := fw.pop("ONIE/DIAG")) is not None:
            try:
                fw["ONIE"], fw["DIAG"] = onie_diag.split("/")
            except ValueError:
                pass

        return FW(
            fw={key: value.strip() for key, value in fw.items() if value is not None},
        )

    @staticmethod
    async def fetch(device: eznet.Device) -> dict[int, FW]:
        show_chassis_fw = await device.run_xml_cmd("show chassis firmware")
        if (fw_info := show_chassis_fw.find("firmware-information/chassis")) is not None:
            return {
                int(fpc[4:]):
                FW.from_xml(e)
                for e in fw_info.findall("chassis-module")
                if "FPC " in (fpc := text(e, "name") or "")
            }
        else:
            raise_error(show_chassis_fw)


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
            "show chassis alarms",
        )
        if (alarm_info := xml.find("alarm-information")) is not None:
            return [
                Alarm.from_xml(alarm)
                for alarm in alarm_info.findall("alarm-detail")
            ]
        else:
            raise_error(xml)


class Chassis:
    def __init__(self, device: eznet.Device):
        self.re = Info(device, RE.fetch)
        self.fpc = Info(device, FPC.fetch)
        self.fw = Info(device, FW.fetch)
        self.alarms = Info(device, Alarm.fetch)
