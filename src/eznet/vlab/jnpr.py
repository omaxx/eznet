from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass
from pathlib import Path

from .topology import Node
from .vm import VM, Disk, Interface
from .vnet import VNet

if TYPE_CHECKING:
    from .vlab import VLab

@dataclass
class vMX(Node):
    version: str
    re_image: str
    fpc_image: str
    re_memory_mb: int = 1024
    re_vcpus: int = 1
    fpc_memory_mb: int = 2048
    fpc_vcpus: int = 3
    double_re: bool = False
    config: str | None = None

    def vms(self, vlab: VLab) -> list[VM]:
        path = vlab.node_path(node_name=self.name)

        images_path = vlab.images_path / "junos/vmx" / self.version
        return [
            VM(
                name=f"{self.name}~re{slot}",
                path = path / f"re{slot}",
                vcpus=self.re_vcpus,
                memory_mb=self.re_memory_mb,
                disks=[
                    Disk(path = images_path / self.re_image, target="vda", snapshot=True),
                    Disk(path = images_path / "vmxhdd.img", target="vdb"),
                    Disk(
                        path = images_path / f"metadata-usb-re{slot}.img",
                        target="vdc",
                        format="raw",
                    ),
                ],
                interfaces=[
                    Interface(type="network", source="mgmt", target=f"{self.name}~re{slot}~mgmt"),
                    Interface(type="network", source=f"{self.name}~int", target=f"{self.name}~re{slot}~int"),
                ],
            )
            for slot in [0, ]
        ] + [
            VM(
                name=f"{self.name}~fpc{slot}",
                machine="pc",
                path = path / f"fpc{slot}",
                vcpus=self.fpc_vcpus,
                memory_mb=self.fpc_memory_mb,
                disks=[
                    Disk(
                        path = images_path / self.fpc_image,
                        target="hda",
                        bus="ide",
                        format="raw",
                    ),
                    Disk(
                        path = images_path / f"metadata-usb-fpc{slot}.img",
                        target="sda",
                        bus="usb",
                        format="raw",
                    ),
                ],
                interfaces=[
                    Interface(type="network", source="mgmt", target=f"{self.name}~fpc{slot}~mgmt"),
                    Interface(type="network", source=f"{self.name}~int", target=f"{self.name}~fpc{slot}~int"),
                    Interface(type="network", source=f"{self.name}~fab", target=f"{self.name}~fpc{slot}~fab"),
                ] + [
                    Interface(type=interface.type, source=interface.name, target=f"{self.name}-{slot}-{i}")
                    for i, interface in enumerate(self.interfaces)
                ],
            )
            for slot in [0, ]
        ]

    def vnets(self, vlab: VLab) -> list[VNet]:
        return [
            VNet(name=f"{self.name}~int"),
            VNet(name=f"{self.name}~fab"),
        ]

    async def init(self, vlab: VLab):
        if self.config is None:
            return

        path = vlab.node_path(node_name=self.name)
        for re in ["re0", ]:
            hdd_image = path / re / "hdd.img"
            staging_dir = (await vlab.host.run("mktemp -d")).stdout.strip()
            mount_dir = (await vlab.host.run("mktemp -d")).stdout.strip()
            try:
                await vlab.host.run(f"guestmount -a {hdd_image} -m /dev/sda {mount_dir}")
                try:
                    await vlab.host.run(f"tar zxvf {mount_dir}/vmm-config.tgz -C {staging_dir}")
                    await vlab.host.run(f"test -d {staging_dir}/config || mkdir {staging_dir}/config")
                    await vlab.host.write_file(f"{staging_dir}/config/juniper.conf", self.config)
                    await vlab.host.run(f"tar zcvf {mount_dir}/vmm-config.tgz {staging_dir}")
                finally:
                    await vlab.host.run(f"guestunmount {mount_dir}")
            finally:
                await vlab.host.run(f"rm -rf {staging_dir}")
                await vlab.host.run(f"rm -rf {mount_dir}")
