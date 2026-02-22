from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from xml.etree.ElementTree import Element, SubElement, tostring, indent, register_namespace

VLAB_NS = "http://eznet/vlab/1.0"
register_namespace("vlab", VLAB_NS)


@dataclass
class DHCPRange:
    start: str
    end: str

    def xml(self) -> Element:
        return Element("range", start=self.start, end=self.end)


@dataclass
class DHCPHost:
    mac: str
    ip: str
    name: str | None = None

    def xml(self) -> Element:
        attrs = {"mac": self.mac, "ip": self.ip}
        if self.name is not None:
            attrs["name"] = self.name
        return Element("host", **attrs)


@dataclass
class DHCP:
    ranges: list[DHCPRange] = field(default_factory=list)
    hosts: list[DHCPHost] = field(default_factory=list)

    def xml(self) -> Element:
        elem = Element("dhcp")
        for r in self.ranges:
            elem.append(r.xml())
        for h in self.hosts:
            elem.append(h.xml())
        return elem


@dataclass
class IP:
    address: str
    netmask: str = "255.255.255.0"
    dhcp: DHCP | None = None

    def xml(self) -> Element:
        elem = Element("ip", address=self.address, netmask=self.netmask)
        if self.dhcp is not None:
            elem.append(self.dhcp.xml())
        return elem


@dataclass
class VNet:
    name: str
    mode: Literal["nat", "route", "open", "bridge"] | None = None
    bridge: str | None = None
    ip: IP | None = None

    def xml(self) -> str:
        root = self._build_network()
        indent(root, space="  ")
        return tostring(root, encoding="unicode", xml_declaration=False)

    def _build_network(self) -> Element:
        network = Element("network")

        SubElement(network, "name").text = self.name

        if self.bridge is not None:
            SubElement(network, "bridge", name=self.bridge)

        if self.mode is not None:
            SubElement(network, "forward", mode=self.mode)

        if self.ip is not None:
            network.append(self.ip.xml())

        return network