from __future__ import annotations

from dataclasses import dataclass, field
from typing import ParamSpec, TypeVar, Callable, Coroutine, Any
import asyncio
import functools
import logging
from pathlib import Path
from xml.etree import ElementTree as ET

import libvirt

from eznet.drivers.ssh import SSH

NS_URI = "https://omaxx.net/vlab"
NS_NAME = "vlab"

TCP_URI = "qemu+tcp://127.0.0.1:{port}/system"
LIBVIRT_PORT = 16509
SOCK_URI = "qemu+unix:///system?socket={socket}"
LIBVIRT_SOCK = "/var/run/libvirt/libvirt-sock"

P = ParamSpec("P")
T = TypeVar("T")

logger = logging.getLogger(__name__)


def sync_to_async(
    method: Callable[P, T]
) -> Callable[P, Coroutine[Any, Any, T]]:
    @functools.wraps(method)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return await asyncio.to_thread(method, *args, **kwargs)
    return wrapper


@dataclass
class VM:
    @dataclass
    class Meta:
        node: str

        @classmethod
        def from_xml(cls, xml: str) -> VM.Meta:
            root = ET.fromstring(xml)
            return cls(node=root.findtext("node"))

        def to_xml(self) -> str:
            root = ET.Element("domain")
            ET.SubElement(root, "node").text = self.node
            return ET.tostring(root, encoding="unicode")

    name: str
    active: bool
    meta: Meta | None = None

    @classmethod
    def from_domain(cls, domain: libvirt.virDomain) -> VM:
        meta: str | None = None
        try:
            meta = domain.metadata(libvirt.VIR_DOMAIN_METADATA_ELEMENT, NS_URI)
        except libvirt.libvirtError:
            pass
        return cls(
            name = domain.name(),
            active = domain.isActive(),
            meta = VM.Meta.from_xml(meta) if meta is not None else None,
        )


@dataclass
class VNet:
    @dataclass
    class Meta:
        nodes: list[str] = field(default_factory=list)

        @classmethod
        def from_xml(cls, xml: str) -> VNet.Meta | None:
            root = ET.fromstring(xml)
            return cls(nodes=[node.text for node in root.findall("nodes/node")])

        def to_xml(self) -> str:
            root = ET.Element("network")
            nodes = ET.SubElement(root, "nodes")
            for node in self.nodes:
                ET.SubElement(nodes, "node").text = node
            return ET.tostring(root, encoding="unicode")

    name: str
    active: bool
    meta: Meta | None = None

    @classmethod
    def from_network(cls, network: libvirt.virNetwork) -> VNet:
        meta: str | None = None
        try:
            meta = network.metadata(libvirt.VIR_NETWORK_METADATA_ELEMENT, NS_URI)
        except libvirt.libvirtError:
            pass
        return cls(
            name = network.name(),
            active = network.isActive(),
            meta = VNet.Meta.from_xml(meta) if meta is not None else None
        )


class Qemu:
    def __init__(
        self,
        ssh: SSH,
    ):
        self._ssh = ssh

        self._port: int | None = None
        self._socket: Path | None = None
        self._virt: libvirt.virConnect | None = None

    async def __aenter__(self):
        await self.open()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def open(self):
        await self._ssh.open()
        try:
            # self._port = await self._ssh.forward_local_port(port=LIBVIRT_PORT)
            self._socket = await self._ssh.forward_local_path(path=LIBVIRT_SOCK)
        except:
            await self._ssh.close()
            raise
        def sync():
            # self._virt = libvirt.open(TCP_URI.format(port=self._port))
            self._virt = libvirt.open(SOCK_URI.format(socket=self._socket))
        try:
            await asyncio.to_thread(sync)
        except:
            # await self._ssh.close_forwarding(self._port)
            # self._port = None
            await self._ssh.close_forwarding(self._socket)
            self._socket = None
            await self._ssh.close()
            raise

    async def close(self):
        def sync():
            self._virt.close()
        await asyncio.to_thread(sync)
        # await self._ssh.close_forwarding(self._port)
        # self._port = None
        await self._ssh.close_forwarding(self._socket)
        self._socket = None
        await self._ssh.close()

    @sync_to_async
    def define_vm(self, xml: str) -> None:
        name = ET.fromstring(xml).find("name").text
        logger.info(f"Define VM `{name}` from\n{xml}")
        try:
            self._virt.defineXML(xml)
            logger.info(f"Define VM `{name}`: done")
        except libvirt.libvirtError as exc:
            logger.error(f"Define VM `{name}`: error: {exc}")

    @sync_to_async
    def vm_set_meta(self, vm_name: str, node_name: str) -> None:
        domain = self._virt.lookupByName(vm_name)
        xml = VM.Meta(node=node_name).to_xml()
        logger.info(f"Set VM `{vm_name}` meta to\n{xml}")
        domain.setMetadata(
            libvirt.VIR_DOMAIN_METADATA_ELEMENT,
            xml,
            NS_NAME,
            NS_URI,
            # flags =
        )

    @sync_to_async
    def define_vnet(self, xml: str) -> None:
        name = ET.fromstring(xml).find("name").text
        logger.info(f"Define VNet `{name}` from\n{xml}")
        try:
            self._virt.networkDefineXML(xml)
            logger.info(f"Define VNet `{name}`: done")
        except libvirt.libvirtError as exc:
            logger.error(f"Define VNet `{name}`: error: {exc}")

    @sync_to_async
    def vnet_set_meta(self, vnet_name: str) -> None:
        network = self._virt.networkLookupByName(vnet_name)
        xml = VNet.Meta().to_xml()
        logger.info(f"Set VNet `{vnet_name}` meta to\n{xml}")
        network.setMetadata(
            libvirt.VIR_NETWORK_METADATA_ELEMENT,
            xml,
            NS_NAME,
            NS_URI,
            # flags =
        )

    @sync_to_async
    def vnet_add_node_tag(self, vnet_name: str, node_name: str) -> None:
        logger.info(f"VNet `{vnet_name}`: add node_tag `{node_name}`")
        network = self._virt.networkLookupByName(vnet_name)
        vnet = VNet.from_network(network)
        logger.info(f"VNet `{vnet_name}` meta:\n{vnet.meta}")
        if vnet.meta is not None and node_name not in vnet.meta.nodes:
            vnet.meta.nodes.append(node_name)
            xml = vnet.meta.to_xml()
            logger.info(f"Set VNet `{vnet_name}` meta to\n{xml}")
            network.setMetadata(
                libvirt.VIR_NETWORK_METADATA_ELEMENT,
                xml,
                NS_NAME,
                NS_URI,
                # flags =
            )

    @sync_to_async
    def vnet_del_node_tag(self, vnet_name: str, node_name: str) -> None:
        network = self._virt.networkLookupByName(vnet_name)
        vnet = VNet.from_network(network)
        if vnet.meta is not None and node_name in vnet.meta.nodes:
            vnet.meta.nodes.remove(node_name)
            network.setMetadata(
                libvirt.VIR_NETWORK_METADATA_ELEMENT,
                vnet.meta.to_xml(),
                NS_NAME,
                NS_URI,
                # flags =
            )

    @sync_to_async
    def start_node(self, node_name: str) -> None:
        for network in self._virt.listAllNetworks():
            vnet = VNet.from_network(network)
            if (meta := vnet.meta) is not None and node_name in meta.nodes:
                if not vnet.active:
                    network.create()

        for domain in self._virt.listAllDomains():
            vm = VM.from_domain(domain)
            if (meta := vm.meta) is not None and meta.node == node_name:
                if not vm.active:
                    domain.create()

    @sync_to_async
    def stop_node(self, node_name: str) -> None:
        for domain in self._virt.listAllDomains():
            vm = VM.from_domain(domain)
            if (meta := vm.meta) is not None and meta.node == node_name:
                if vm.active:
                    domain.destroy()

        for network in self._virt.listAllNetworks():
            vnet = VNet.from_network(network)
            if (meta := vnet.meta) is not None and node_name in meta.nodes:
                if vnet.active and len(network.listAllPorts()) == 0:
                    network.destroy()

    @sync_to_async
    def undefine_node(self, node_name: str) -> None:
        for domain in self._virt.listAllDomains():
            vm = VM.from_domain(domain)
            if (meta := vm.meta) is not None and meta.node == node_name:
                if vm.active:
                    domain.destroy()
                domain.undefine()

        for network in self._virt.listAllNetworks():
            vnet = VNet.from_network(network)
            if vnet.meta is not None and node_name in vnet.meta.nodes:
                vnet.meta.nodes.remove(node_name)
                network.setMetadata(
                    libvirt.VIR_NETWORK_METADATA_ELEMENT,
                    vnet.meta.to_xml(),
                    NS_NAME,
                    NS_URI,
                    # flags =
                )

    @sync_to_async
    def undefine_vnet(self, name: str) -> None:
        try:
            network = self._virt.networkLookupByName(name)
            network.undefine()
        except libvirt.libvirtError as exc:
            logger.error(f"Undefine {name}: {exc}")

    async def list_vms(self) -> list[VM]:
        def sync():
            return [
                VM.from_domain(domain)
                for domain in self._virt.listAllDomains()
            ]
        return await asyncio.to_thread(sync)

    async def list_vnets(self) -> list[VNet]:
        def sync():
            return [
                VNet.from_network(network)
                for network in self._virt.listAllNetworks()
            ]
        return await asyncio.to_thread(sync)
