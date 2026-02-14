"""Libvirt network XML builder for KVM virtual networks."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Literal
from xml.etree.ElementTree import Element, SubElement, tostring, indent


@dataclass
class DHCPRange:
    """DHCP address range within a network.

    Attributes:
        start: First address in the range (e.g. '192.168.100.100').
        end: Last address in the range (e.g. '192.168.100.254').
    """

    start: str
    end: str

    def xml(self) -> Element:
        """Builds the <range> element.

        Returns:
            An ``Element`` representing this DHCP range.
        """
        return Element("range", start=self.start, end=self.end)


@dataclass
class DHCPHost:
    """Static DHCP reservation.

    Attributes:
        mac: MAC address of the host.
        ip: IP address to assign.
        name: Optional hostname for DNS.
    """

    mac: str
    ip: str
    name: str | None = None

    def xml(self) -> Element:
        """Builds the <host> element.

        Returns:
            An ``Element`` representing this DHCP host reservation.
        """
        attrs = {"mac": self.mac, "ip": self.ip}
        if self.name is not None:
            attrs["name"] = self.name
        return Element("host", **attrs)


@dataclass
class DHCP:
    """DHCP configuration for a network.

    Attributes:
        ranges: Dynamic address ranges.
        hosts: Static host reservations.
    """

    ranges: list[DHCPRange] = field(default_factory=list)
    hosts: list[DHCPHost] = field(default_factory=list)

    def xml(self) -> Element:
        """Builds the <dhcp> element.

        Returns:
            An ``Element`` representing this DHCP configuration.
        """
        elem = Element("dhcp")
        for r in self.ranges:
            elem.append(r.xml())
        for h in self.hosts:
            elem.append(h.xml())
        return elem


@dataclass
class IP:
    """IP configuration for a network.

    Attributes:
        address: Gateway address for the network (e.g. '192.168.100.1').
        netmask: Subnet mask (e.g. '255.255.255.0').
        dhcp: Optional DHCP configuration.
    """

    address: str
    netmask: str = "255.255.255.0"
    dhcp: DHCP | None = None

    def xml(self) -> Element:
        """Builds the <ip> element.

        Returns:
            An ``Element`` representing this IP configuration.
        """
        elem = Element("ip", address=self.address, netmask=self.netmask)
        if self.dhcp is not None:
            elem.append(self.dhcp.xml())
        return elem


@dataclass
class VNet:
    """Libvirt virtual network definition.

    Produces libvirt-compatible network XML via the ``xml()`` method.

    Forward modes:

    - **nat**: VMs reach the outside via NAT through the host.
    - **route**: Host acts as a router, no address translation.
    - **open**: Forwarding with no firewall rules.
    - **bridge**: Uses an existing host bridge directly.
    - **None**: Isolated network, no forwarding (VMs talk only to each other).

    Attributes:
        name: Network name (must be unique per host).
        mode: Forwarding mode. ``None`` for isolated networks.
        bridge: Bridge device name on the host (e.g. 'virbr1').
            Optional; libvirt auto-generates one if omitted.
        ip: IP/gateway configuration. Optional for bridge mode.
        domain: DNS domain name for the network. Optional.
        uuid: Network UUID. Auto-generated if not provided.
    """

    name: str
    mode: Literal["nat", "route", "open", "bridge"] | None = None
    bridge: str | None = None
    ip: IP | None = None
    domain: str | None = None
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))

    def xml(self) -> str:
        """Builds and returns the libvirt network XML string.

        Returns:
            A formatted XML string ready for ``virConnect.networkDefineXML()``.
        """
        root = self._build_network()
        indent(root, space="  ")
        return tostring(root, encoding="unicode", xml_declaration=False)

    def _build_network(self) -> Element:
        """Constructs the full <network> element tree."""
        network = Element("network")

        SubElement(network, "name").text = self.name
        SubElement(network, "uuid").text = self.uuid

        if self.bridge is not None:
            SubElement(network, "bridge", name=self.bridge)

        if self.mode is not None:
            SubElement(network, "forward", mode=self.mode)

        if self.domain is not None:
            SubElement(network, "domain", name=self.domain)

        if self.ip is not None:
            network.append(self.ip.xml())

        return network