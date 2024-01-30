from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List

from lxml.etree import _Element  # noqa

from eznet.parsers.xml import text, number, timestamp
import eznet


@dataclass
class AF:
    address: Optional[str]
    network: Optional[str]

    @staticmethod
    def from_xml(xml: _Element) -> AF:
        return AF(
            address=text(xml, "interface-address/ifa-local"),
            network=text(xml, "interface-address/ifa-destination"),
        )


@dataclass
class UnitTraffic:
    input_packets: Optional[int]
    output_packets: Optional[int]

    @staticmethod
    def from_xml(xml: _Element) -> UnitTraffic:
        return UnitTraffic(
            input_packets=number(xml, "traffic-statistics/input-packets"),
            output_packets=number(xml, "traffic-statistics/output-packets"),
        )


@dataclass
class Unit:
    description: str
    family: Dict[str, AF]
    traffic: UnitTraffic

    @staticmethod
    def from_xml(xml: _Element) -> Unit:
        return Unit(
            description=text(xml, "description"),
            family={
                text(e, "address-family-name"): AF.from_xml(e)
                for e in xml.findall("address-family")
            },
            traffic=UnitTraffic.from_xml(xml),
        )


@dataclass
class Traffic:
    input_bps: int
    input_pps: int
    output_bps: int
    output_pps: int

    @staticmethod
    def from_xml(xml: _Element) -> Traffic:
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
    units: Dict[int, Unit]
    traffic: Traffic
    ae: Optional[str]

    @staticmethod
    def from_xml(xml: _Element) -> Interface:
        ae = text(xml, "logical-interface/address-family[address-family-name=\"aenet\"]ae-bundle-name")
        if ae is not None:
            ae = ae.split(".")[0]
        return Interface(
            description=text(xml, "description"),
            admin=text(xml, "admin-status"),
            oper=text(xml, "oper-status"),
            speed=text(xml, "speed"),
            units={
                int(text(e, "name").split(".")[1]): Unit.from_xml(e)
                for e in xml.findall("logical-interface")
            },
            traffic=Traffic.from_xml(xml),
            ae=ae,
        )

    @classmethod
    async def fetch(cls, device: eznet.Device) -> Optional[Dict[str, Interface]]:
        show_interfaces = await device.junos.run_xml_cmd("show interfaces")
        if show_interfaces is not None:
            interface_information = show_interfaces.find("interface-information")
            return {
                text(e, "name"): Interface.from_xml(e)
                for e in interface_information.findall("physical-interface")
                if text(e, "name")[:2] in ["ae", "ge", "xe", "et"]
            }
