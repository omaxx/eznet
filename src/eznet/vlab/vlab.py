from __future__ import annotations

import logging
from pathlib import Path

from eznet.host import Host
from eznet.vlab.nodes import Node


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

    async def create(self, node: Node) -> None:
        await self.host.mkdir(self.vms_path / node.name)
        for vm in node.vms(self):
            await self.host.mkdir(vm.path)
            for disk in vm.disks:
                if disk.path.is_absolute():
                    await self.copy(disk.path, vm.path / disk.path.name)
            await self.host.qemu.define_vm(vm.name, vm.xml())
        for vnet in node.vnets(self):
            await self.host.qemu.define_vnet(vnet.name, vnet.xml())
        await node.init(self)

    async def start(self, node_name: str) -> None:
        for vm in await self.host.qemu.list_vms(node_name=node_name):
            await self.host.qemu.start_vm(vm.name)

    async def stop(self, node_name: str) -> None:
        for vm in await self.host.qemu.list_vms(node_name=node_name):
            await self.host.qemu.stop_vm(vm.name)

    async def delete(self, node_name: str) -> None:
        for vm in await self.host.qemu.list_vms(node_name=node_name):
            await self.host.qemu.undefine_vm(vm.name)
        await self.host.rmdir(self.vms_path / node_name)
