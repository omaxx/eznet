import statistics
from dataclasses import dataclass
from typing import Dict, List, Union

from ..data import Data
from ..drivers import SSH
from .get import get_xml, number, text


@dataclass
class Peer:
    device: str
    interface: str

    @classmethod
    def from_xml(cls, lldp_neighbors, interface_name):
        xpath = f"//lldp-neighbor-information[lldp-local-port-id='{interface_name}']"
        if len(lldp_neighbors.xpath(xpath)) == 0:
            return None
        else:
            return cls(
                device=text(lldp_neighbors, f"{xpath}/lldp-remote-system-name"),
                interface=text(lldp_neighbors, f"{xpath}/lldp-remote-port-id")
            )


@dataclass
class XCVR:
    description: str

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
                return cls(
                    description=text(xml, xpath+"/description"),
                    # speed=description.split("-")[1],
                    # type=description.split("-")[2],
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
    def from_xml(cls,
                 interface_name,
                 interface_information,
                 lldp_neighbors=None,
                 chassis_hw=None
                 ):
        xpath = f"//physical-interface[name='{interface_name}']"
        if len(interface_information.xpath(xpath)) == 0:
            return None
        else:
            if interface_name[:2] in ["ge", "xe", "et"]:
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
            else:
                return cls(
                    oper=text(interface_information, f"{xpath}/oper-status"),
                    admin=text(interface_information, f"{xpath}/admin-status"),
                    traffic_statistics=TrafficStatistics.from_xml(interface_information, interface_name),
                )


def get_interfaces_info(ssh: SSH) -> Dict[str, Interface]:
    interface_information = get_xml(ssh, "show interfaces", "//interface-information")
    lldp_neighbors = get_xml(ssh, "show lldp neighbors", "//lldp-neighbors-information")
    chassis_hw = get_xml(ssh, "show chassis hardware", "//chassis-inventory")
    return {
        text(e, "name"): Interface.from_xml(
            text(e, "name"),
            interface_information,
            lldp_neighbors,
            chassis_hw,
        )
        for e in interface_information.xpath("//physical-interface")
        if text(e, "name")[:2] in ["ae", "ge", "xe", "et"]
    }


def lb(rates: List[Union[int, float]]) -> Union[float, None]:
    if len(rates) == 0:
        return None
    try:
        return statistics.pstdev(rates)/statistics.mean(rates)
    except ZeroDivisionError:
        return None
