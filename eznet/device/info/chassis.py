from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, Optional, List

from attrs import define
from lxml.etree import _Element  # noqa

from eznet.parser.xml import text, number, timestamp
import eznet
from eznet.data import Data


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
            "show chassis alarms",
        )
        if xml is not None:
            alarm_info = xml.find("alarm-information")
            if alarm_info is not None:
                return [
                    Alarm.from_xml(alarm)
                    for alarm in alarm_info.findall("alarm-detail")
                ]


@define
class Port:
    cable_type: Optional[str]
    fiber_mode: Optional[str]
    wavelength: Optional[str]

    @staticmethod
    def from_xml(port: _Element) -> Port:
        return Port(
            cable_type=text(port, "cable-type"),
            fiber_mode=text(port, "fiber-mode"),
            wavelength=text(port, "wavelength"),
        )


@define
class PIC:
    state: Optional[str]
    type: Optional[str]
    ports: Optional[Dict[int, Port]] = None

    @staticmethod
    def from_xml(pic: _Element) -> PIC:
        return PIC(
            state=text(pic, "pic-state"),
            type=text(pic, "pic-type"),
        )


@define
class FPC:
    state: Optional[str]
    comment: Optional[str]
    cpu_utilization_total: Optional[int]
    cpu_utilization_interrupt: Optional[int]
    memory_dram: Optional[int]
    memory_heap_utilization: Optional[int]
    memory_buffer_utilization: Optional[int]
    description: Optional[str]
    pics: Dict[int, PIC]

    @staticmethod
    def from_xml(fpc: _Element) -> FPC:
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
                number(pic, "pic-slot"): PIC.from_xml(pic)
                for pic in fpc.findall("pic")
            },
        )

    @staticmethod
    async def fetch(device: eznet.device.Device, get_ports: bool = False) -> Optional[Dict[int, FPC]]:
        show_chassis_fpc = await device.junos.run_xml_cmd("show chassis fpc pic-status")
        if show_chassis_fpc is not None:
            fpc_info = show_chassis_fpc.find("fpc-information")
            if fpc_info is not None:
                fpc_dict = {
                    number(fpc, "slot"): FPC.from_xml(fpc)
                    for fpc in fpc_info.findall("fpc")
                }

                if not get_ports:
                    return fpc_dict
                else:
                    for fpc_number, fpc in fpc_dict.items():
                        for pic_number, pic in fpc.pics.items():
                            xml = await device.junos.run_xml_cmd(
                                f"show chassis pic fpc-slot {fpc_number} pic-slot {pic_number}",
                            )
                            if xml is not None:
                                pic.ports = {
                                    number(port, "port-number"): Port.from_xml(port)
                                    for port in xml.findall("fpc-information/fpc/pic-detail/port-information/port")
                                }
                    return fpc_dict


@define
class FW:
    fw: Dict[str, str]

    @staticmethod
    def from_xml(xml: _Element) -> FW:
        fw = {
            text(e, "type"): text(e, "firmware-version")
            for e in xml.findall("firmware")
        }
        if "ONIE/DIAG" in fw:
            try:
                fw["ONIE"], fw["DIAG"] = fw.pop("ONIE/DIAG").split("/")
            except ValueError:
                pass
        fw = {key: value.strip() for key, value in fw.items() if value is not None}

        return FW(
            fw=fw,
        )

    @staticmethod
    async def fetch(device: eznet.device.Device) -> Optional[Dict[int, FW]]:
        show_chassis_fw = await device.junos.run_xml_cmd("show chassis firmware")
        if show_chassis_fw is not None:
            fw_info = show_chassis_fw.find("firmware-information/chassis")
            if fw_info is not None:
                return {
                    int(text(e, "name")[4:]):
                    FW.from_xml(e)
                    for e in fw_info.findall("chassis-module")
                    if "FPC " in text(e, "name")
                }


@define
class RE:
    model: Optional[str]
    status: Optional[str]
    mastership: Optional[str]
    start_time: Optional[datetime]
    reboot_reason: Optional[str]

    @staticmethod
    def from_xml(xml: _Element) -> RE:
        return RE(
            model=text(xml, "model"),
            status=text(xml, "status"),
            mastership=text(xml, "mastership-state"),
            start_time=timestamp(xml, "start-time"),
            reboot_reason=text(xml, "last-reboot-reason"),
        )

    @staticmethod
    async def fetch(device: eznet.device.Device) -> Optional[Dict[int, RE]]:
        show_chassis_re = await device.junos.run_xml_cmd("show chassis routing-engine")
        if show_chassis_re is not None:
            re_information = show_chassis_re.find("route-engine-information")
            if re_information is not None:
                return {
                    number(e, "slot"):
                    RE.from_xml(e) for e in re_information.findall("route-engine")
                    if number(e, "slot") is not None
                }


class Chassis:
    def __init__(self, device: eznet.device.Device):
        self.fpc = Data(FPC.fetch, device)
        self.re = Data(RE.fetch, device)
        self.fw = Data(FW.fetch, device)
