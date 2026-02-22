from __future__ import annotations

from typing import TYPE_CHECKING
import logging
from pathlib import Path
import asyncio

from eznet.host import Host

from .qemu import Qemu, LIBVIRT_SOCK
from .topology import Network

DEFAULT_BASE_PATH = "/var/vlab"
DEFAULT_IMAGES_DIR = "images"
DEFAULT_VMS_DIR = "vms"

if TYPE_CHECKING:
    from .topology import Node


class VLab:
    def __init__(
        self,
        host: Host,
        base_path: str = DEFAULT_BASE_PATH,
    ) -> None:
        self.host = host
        self.base_path = Path(base_path)

        self.images_path = self.base_path / DEFAULT_IMAGES_DIR
        self.vms_path = self.base_path / DEFAULT_VMS_DIR
        self.logger = logging.getLogger(f"{__name__}.{host.name}")

        self._port: int | None = None
        self._socket: Path | None = None
        self._qemu = Qemu()

    def node_path(self, node_name) -> Path:
        return self.vms_path / node_name

    async def __aenter__(self):
        await self.open()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def open(self):
        await self.host.ssh.open()
        try:
            # self._port = await self._ssh.forward_local_port(port=LIBVIRT_PORT)
            self._socket = await self.host.ssh.forward_local_path(path=LIBVIRT_SOCK)
        except:
            await self.host.ssh.close()
            raise

        try:
            await asyncio.to_thread(self._qemu.open, socket=self._socket)
        except:
            # await self._ssh.close_forwarding(self._port)
            # self._port = None
            await self.host.ssh.close_forwarding(self._socket)
            self._socket = None
            await self.host.ssh.close()
            raise

    async def close(self):
        await asyncio.to_thread(self._qemu.close)
        # await self._ssh.close_forwarding(self._port)
        # self._port = None
        await self.host.ssh.close_forwarding(self._socket)
        self._socket = None
        await self.host.ssh.close()

    async def copy(
        self,
        src: str | Path,
        dst: str | Path,
        force: bool = False,
    ) -> None:
        test = f"test -e {dst}" if not force else "false"
        await self.host.run(f"{test} || rsync -a {src} {dst}")

    async def make_snapshot(
        self,
        src: str | Path,
        dst: str | Path,
        force: bool = False,
    ) -> None:
        test = f"test -e {dst}" if not force else "false"
        await self.host.run(
            f"{test} || qemu-img create -f qcow2 -b {src} -F qcow2 {dst}"
        )

    async def create_node(self, node: Node) -> None:
        for interface in node.interfaces:
            if isinstance(interface, Network):
                # await self.host.qemu.define_vnet(interface.vnet().xml())
                await asyncio.to_thread(
                    self._qemu.vnet_add_node_tag,
                    interface.vnet().name,
                    node_name=node.name,
                )
        for vnet in node.vnets(self):
            await asyncio.to_thread(
                self._qemu.define_vnet,
                vnet.xml()
            )
            await asyncio.to_thread(
                self._qemu.vnet_add_node_tag,
                vnet.name,
                node_name=node.name,
            )

        await self.host.mkdir(self.node_path(node.name))

        for vm in node.vms(self):
            await self.host.mkdir(vm.path)
            for disk in vm.disks:
                if disk.path.is_absolute():
                    if disk.snapshot:
                        await self.make_snapshot(disk.path, vm.path / disk.path.name)
                    else:
                        await self.copy(disk.path, vm.path / disk.path.name)
            await asyncio.to_thread(
                self._qemu.define_vm,
                vm.xml(),
                node_name=node.name,
            )
        await node.init(self)

    async def create_network(self, network: Network) -> None:
        vnet = network.vnet()
        await asyncio.to_thread(
            self._qemu.define_vnet,
            vnet.xml(),
        )

    async def start_node(self, node_name: str) -> None:
        await asyncio.to_thread(
            self._qemu.start_node,
            node_name=node_name,
        )

    async def stop_node(self, node_name: str) -> None:
        await asyncio.to_thread(
            self._qemu.stop_node,
            node_name=node_name,
        )

    # async def start_network(self, network_name: str) -> None:
    #     await self.host.qemu.start_vnet(network_name)
    #
    # async def stop_network(self, network_name: str) -> None:
    #     await self.host.qemu.stop_vnet(network_name)
    #
    async def delete_node(self, node_name: str) -> None:
        await asyncio.to_thread(
            self._qemu.undefine_node_vms,
            node_name,
        )
        await asyncio.to_thread(
            self._qemu.vnet_del_node_tag,
            node_name,
        )
        await asyncio.to_thread(
            self._qemu.undefine_orphan_networks,
        )
        await self.host.rmdir(self.node_path(node_name))

    async def delete_network(self, network_name: str) -> None:
        await asyncio.to_thread(
            self._qemu.undefine_vnet,
            network_name,
        )

    async def list_vms(self):
        return await asyncio.to_thread(self._qemu.list_vms)

    async def list_vnets(self):
        return await asyncio.to_thread(self._qemu.list_vnets)
