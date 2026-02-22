from __future__ import annotations

import logging
from pathlib import Path

from eznet.host import Host

from .nodes import Node, Network


DEFAULT_BASE_PATH = "/var/vlab"
DEFAULT_IMAGES_DIR = "images"
DEFAULT_VMS_DIR = "vms"


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
                # await self.host.qemu.vnet_set_meta(interface.vnet().name)
                await self.host.qemu.vnet_add_node_tag(interface.vnet().name, node_name=node.name)

        for vnet in node.vnets(self):
            await self.host.qemu.define_vnet(vnet.xml())
            await self.host.qemu.vnet_set_meta(vnet.name)
            await self.host.qemu.vnet_add_node_tag(vnet.name, node_name=node.name)

        await self.host.mkdir(node.path(self))

        for vm in node.vms(self):
            await self.host.mkdir(vm.path)
            for disk in vm.disks:
                if disk.path.is_absolute():
                    if disk.snapshot:
                        await self.make_snapshot(disk.path, vm.path / disk.path.name)
                    else:
                        await self.copy(disk.path, vm.path / disk.path.name)
            await self.host.qemu.define_vm(vm.xml())
            await self.host.qemu.vm_set_meta(vm.name, node_name=node.name)
        await node.init(self)

    async def create_network(self, network: Network) -> None:
        vnet = network.vnet()
        await self.host.qemu.define_vnet(vnet.xml())
        await self.host.qemu.vnet_set_meta(vnet.name)

    async def start_node(self, node_name: str) -> None:
        await self.host.qemu.start_node(node_name)

    async def stop_node(self, node_name: str) -> None:
        await self.host.qemu.stop_node(node_name)

    # async def start_network(self, network_name: str) -> None:
    #     await self.host.qemu.start_vnet(network_name)
    #
    # async def stop_network(self, network_name: str) -> None:
    #     await self.host.qemu.stop_vnet(network_name)
    #
    async def delete_node(self, node_name: str) -> None:
        await self.host.qemu.undefine_node(node_name)
        # for vnet in await self.host.qemu.list_vnets(node_name=node_name):
        #     await self.host.qemu.undefine_vnet(vnet.name)
        await self.host.rmdir(self.vms_path / node_name)

    async def delete_network(self, network_name: str) -> None:
        await self.host.qemu.undefine_vnet(network_name)
