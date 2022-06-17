from typing import Union

from dataclasses import dataclass
import statistics

from ..drivers import SSH
from ..data import Data
from .get import get_xml, text, number


@dataclass
class Peer:
    name: str
    port: str

    @classmethod
    def from_xml(cls, lldp_neighbors, interface_name):
        xpath = f"//lldp-neighbor-information[lldp-local-port-id='{interface_name}']"
        if len(lldp_neighbors.xpath(xpath)) == 0:
            return None
        else:
            return cls(
                name=text(lldp_neighbors, f"{xpath}/lldp-remote-system-name"),
                port=text(lldp_neighbors, f"{xpath}/lldp-remote-port-id")
            )


@dataclass
class XCVR:
    speed: str
    type: str

    @classmethod
    def from_xml(cls, xml, interface_name):
        fpc, pic, port = interface_name.split("-")[1].split(":")[0].split("/")
        for xpath in [
            f"//chassis-module[name='FPC {fpc}']" +
            f"/chassis-sub-module[name='PIC {pic}']" +
            f"/chassis-sub-sub-module[name='Xcvr {port}']",
            f"//chassis-module[name='FPC {fpc}']" +
            f"//chassis-sub-sub-module[name='PIC {pic}']" +
            f"/chassis-sub-sub-sub-module[name='Xcvr {port}']",
        ]:
            if len(xml.xpath(xpath)) == 1:
                description = text(xml, xpath+"/description")
                return cls(
                    speed=description.split("-")[1],
                    type=description.split("-")[2],
                )
        return None


@dataclass
class TrafficStatistics:
    input_bps: int
    input_pps: int
    output_bps: int
    output_pps: int

    @classmethod
    def from_xml(cls, interface_information, interface_name):
        xpath = f"//physical-interface[name='{interface_name}']"
        return cls(
            input_bps=number(interface_information, f"{xpath}/traffic-statistics/input-bps"),
            input_pps=number(interface_information, f"{xpath}/traffic-statistics/input-pps"),
            output_bps=number(interface_information, f"{xpath}/traffic-statistics/output-bps"),
            output_pps=number(interface_information, f"{xpath}/traffic-statistics/output-pps"),
        )


@dataclass
class Interface:
    oper: str
    admin: str
    traffic_statistics: TrafficStatistics
    ae: str = None
    peer: Peer = None
    xcvr: XCVR = None

    @classmethod
    def from_xml(cls, interface_information, interface_name, interface_data, lldp_neighbors=None, chassis_hw=None):
        xpath = f"//physical-interface[name='{interface_name}']"
        if len(interface_information.xpath(xpath)) == 0:
            return None
        else:
            return cls(
                oper=text(interface_information, f"{xpath}/oper-status"),
                admin=text(interface_information, f"{xpath}/admin-status"),
                traffic_statistics=TrafficStatistics.from_xml(interface_information, interface_name),
                ae=text(interface_information,
                        f"{xpath}/logical-interface/address-family[address-family-name='aenet']"
                        f"/ae-bundle-name").split(".")[0],
                peer=Peer.from_xml(lldp_neighbors, interface_name) if lldp_neighbors is not None else None,
                xcvr=XCVR.from_xml(chassis_hw, interface_name) if chassis_hw is not None else None,
            )


@dataclass
class AEInterface:
    oper: str
    admin: str
    traffic_statistics: TrafficStatistics
    members: dict[str, Interface] = None

    @classmethod
    def from_xml(cls, interface_information, interface_name, interface_data, lldp_neighbors=None, chassis_hw=None):
        xpath = f"//physical-interface[name='{interface_name}']"
        if len(interface_information.xpath(xpath)) == 0:
            return None
        else:
            return cls(
                oper=text(interface_information, f"{xpath}/oper-status"),
                admin=text(interface_information, f"{xpath}/admin-status"),
                traffic_statistics=TrafficStatistics.from_xml(interface_information, interface_name),
                members={
                    member_name: Interface.from_xml(
                        interface_information,
                        member_name, member_data,
                        lldp_neighbors, chassis_hw
                    )
                    for member_name, member_data in interface_data.members.items()
                } if interface_data.members is not None else None,
            )

    @property
    def lb(self):
        return {
            "output_bps": lb([member.traffic_statistics.output_bps for member in self.members.values()]),
            "output_pps": lb([member.traffic_statistics.output_pps for member in self.members.values()]),
        }


def get_interface_info(ssh: SSH, data: Data) -> dict[str, Interface]:
    interface_information = get_xml(ssh, "show interfaces", "//interface-information")
    lldp_neighbors = get_xml(ssh, "show lldp neighbors", "//lldp-neighbors-information")
    chassis_hw = get_xml(ssh, "show chassis hardware", "//chassis-inventory")
    return {
        interface_name: (Interface, AEInterface)[interface_name[0:2] == "ae"].from_xml(
            interface_information,
            interface_name, interface_data,
            lldp_neighbors, chassis_hw
        )
        for interface_name, interface_data in data.interfaces.items()
    } if data.interfaces is not None else None


def lb(rates: list[Union[int, float]]) -> float:
    return statistics.pstdev(rates)/statistics.mean(rates)


def interfaces_lb(interfaces: dict[str, Interface], names: list[str]):
    try:
        return {
            "output_bps": lb([
                interfaces[interface_name].traffic_statistics.output_bps
                for interface_name in names
            ]),
            "output_pps": lb([
                interfaces[interface_name].traffic_statistics.output_pps
                for interface_name in names
            ]),
        }
    except KeyError:
        return None
