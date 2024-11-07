from __future__ import annotations

from typing import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from xml.etree.ElementTree import Element
from lxml.etree import _Element

import eznet
from eznet.parsers.xml import text, timestamp, number

from .info import Info, raise_error


@dataclass
class AF:
    address: Optional[str]
    network: Optional[str]

    @staticmethod
    def from_xml(xml: Element) -> AF:
        return AF(
            address=text(xml, "interface-address/ifa-local"),
            network=text(xml, "interface-address/ifa-destination"),
        )


@dataclass
class UnitTraffic:
    input_packets: Optional[int]
    output_packets: Optional[int]

    @staticmethod
    def from_xml(xml: Element) -> UnitTraffic:
        return UnitTraffic(
            input_packets=number(xml, "traffic-statistics/input-packets"),
            output_packets=number(xml, "traffic-statistics/output-packets"),
        )


@dataclass
class Unit:
    description: Optional[str]
    family: dict[str, AF]
    traffic: UnitTraffic

    @staticmethod
    def from_xml(xml: Element) -> Unit:
        return Unit(
            description=text(xml, "description"),
            family={
                name: AF.from_xml(e)
                for e in xml.findall("address-family")
                if (name := text(e, "address-family-name")) is not None
            },
            traffic=UnitTraffic.from_xml(xml),
        )


@dataclass
class Traffic:
    input_bps: Optional[int]
    input_pps: Optional[int]
    output_bps: Optional[int]
    output_pps: Optional[int]

    @staticmethod
    def from_xml(xml: Element) -> Traffic:
        return Traffic(
            input_bps=number(xml, "traffic-statistics/input-bps"),
            input_pps=number(xml, "traffic-statistics/input-pps"),
            output_bps=number(xml, "traffic-statistics/output-bps"),
            output_pps=number(xml, "traffic-statistics/output-pps"),
        )


@dataclass
class Interface:
    admin: Optional[str]
    oper: Optional[str]
    description: Optional[str]
    speed: Optional[str]
    units: dict[int, Unit]
    traffic: Traffic
    ae: Optional[str]

    @staticmethod
    def from_xml(xml: Element) -> Interface:
        ae = text(xml, "logical-interface/address-family[address-family-name=\"aenet\"]ae-bundle-name")
        if ae is not None:
            ae = ae.split(".")[0]
        return Interface(
            description=text(xml, "description"),
            admin=text(xml, "admin-status"),
            oper=text(xml, "oper-status"),
            speed=text(xml, "speed"),
            units={
                int(name.split(".")[1]): Unit.from_xml(e)
                for e in xml.findall("logical-interface")
                if (name := text(e, "name")) is not None
            },
            traffic=Traffic.from_xml(xml),
            ae=ae,
        )

    @classmethod
    async def fetch(
        cls,
        device: eznet.Device,
        # name_filter: Callable[[str], bool] = lambda name: name.split("-")[0] in ("ge", "xe", "et") or name[:2] in ("ae",),
    ) -> dict[str, Interface]:
        show_interfaces = await device.run_xml_cmd("show interfaces")
        if (interface_information := show_interfaces.find("interface-information")) is not None:
            return {
                name: Interface.from_xml(e)
                for e in interface_information.findall("physical-interface")
                if (name := text(e, "name")) is not None # and name_filter(name)
            }
        else:
            raise_error(show_interfaces)
