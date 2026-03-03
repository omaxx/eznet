from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass, field

from eznet.jnpr.vars import Vars

from eznet.vlab.topology import Node, Link, Bridge
from eznet.vlab.vm import VM, Disk, Interface
from eznet.vlab.vnet import VNet

if TYPE_CHECKING:
    from eznet.vlab import VLab

MAC = "ca:ff:ee"

@dataclass(kw_only=True)
class vMX(Node):
    type = "jnpr/vmx"
    version: str
    re_image: str
    fpc_image: str
    re_memory_mb: int = 1024
    re_vcpus: int = 1
    fpc_memory_mb: int = 2048
    fpc_vcpus: int = 3
    double_re: bool = False
    vars: Vars | None = None
    mgmt: Link = field(default_factory=lambda: Bridge("mgmt"))

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
                        path = (
                            images_path / f"metadata-usb-re{slot}.img"
                            if self.double_re else
                            images_path / "metadata-usb-re.img"
                        ),
                        target="vdc",
                        format="raw",
                    ),
                ],
                interfaces=[
                    Interface(
                        type=self.mgmt.type,
                        source=self.mgmt.name,
                        target=f"{self.name}~re{slot}~mgmt",
                        mac=(
                            f"{MAC}:{self.id}:{10 + slot}:00"
                            if self.id is not None
                            else None
                        ),
                    ),
                    Interface(
                        type="network",
                        source=f"{self.name}~int",
                        target=f"{self.name}~re{slot}~int",
                        mac=(
                            f"{MAC}:{self.id}:{10 + slot}:01"
                            if self.id is not None
                            else None
                        ),
                    ),
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
                    Interface(
                        type=self.mgmt.type,
                        source=self.mgmt.name,
                        target=f"{self.name}~fpc{slot}~mgmt",
                        mac=(
                            f"{MAC}:{self.id}:{slot}:0a"
                            if self.id is not None
                            else None
                        ),
                    ),
                    Interface(
                        type="network",
                        source=f"{self.name}~int",
                        target=f"{self.name}~fpc{slot}~int",
                        mac=(
                            f"{MAC}:{self.id}:{slot}:0b"
                            if self.id is not None
                            else None
                        ),
                    ),
                    Interface(
                        type="network",
                        source=f"{self.name}~fab",
                        target=f"{self.name}~fpc{slot}~fab",
                        mac=(
                            f"{MAC}:{self.id}:{slot}:0c"
                            if self.id is not None
                            else None
                        ),
                    ),
                ] + [
                    Interface(
                        type=interface.type,
                        source=interface.name,
                        target=f"{self.name}-{slot}-{i}",
                        mac=(
                            f"{MAC}:{self.id}:{slot}:{i}"
                            if self.id is not None
                            else None
                        ),
                    )
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
        if self.vars is None:
            return

        path = vlab.node_path(node_name=self.name)
        for slot in [0, ]:
            hdd_image = (
                path / f"re{slot}" / f"metadata-usb-re{slot}.img"
                if self.double_re else
                path / f"re{slot}" / "metadata-usb-re.img"
            )
            staging_dir = (await vlab.host.run("mktemp -d")).stdout.strip()
            mount_dir = (await vlab.host.run("mktemp -d")).stdout.strip()
            try:
                await vlab.host.run(f"guestmount -a {hdd_image} -m /dev/sda {mount_dir}")
                try:
                    await vlab.host.run(f"tar zxvf {mount_dir}/vmm-config.tgz -C {staging_dir}")
                    await vlab.host.run(f"mkdir -p {staging_dir}/config")
                    await vlab.host.write_file(f"{staging_dir}/config/juniper.conf", self.vars.config())
                    await vlab.host.run(f"tar zcvf {mount_dir}/vmm-config.tgz -C {staging_dir} .")
                finally:
                    await vlab.host.run(f"guestunmount {mount_dir}")
            finally:
                await vlab.host.run(f"rm -rf {staging_dir}")
                await vlab.host.run(f"rm -rf {mount_dir}")


@dataclass(kw_only=True)
class vQFX(Node):
    type = "jnpr/vqfx"
    version: str
    re_image: str
    fpc_image: str
    re_memory_mb: int = 1024
    re_vcpus: int = 1
    fpc_memory_mb: int = 1024
    fpc_vcpus: int = 1
    double_re: bool = False
    vars: Vars | None = None
    mgmt: Link = field(default_factory=lambda: Bridge("mgmt"))

    def vms(self, vlab: VLab) -> list[VM]:
        path = vlab.node_path(node_name=self.name)

        images_path = vlab.images_path / "junos/vqfx" / self.version
        return [
            VM(
                name=f"{self.name}~re{slot}",
                machine="pc",
                path = path / f"re{slot}",
                vcpus=self.re_vcpus,
                memory_mb=self.re_memory_mb,
                disks=[
                    Disk(path = images_path / self.re_image, target="hda", bus="ide"),
                ],
                interfaces=[
                    Interface(
                        type=self.mgmt.type,
                        source=self.mgmt.name,
                        target=f"{self.name}~re{slot}~mgmt",
                        mac=(
                            f"{MAC}:{self.id}:{10 + slot}:00"
                            if self.id is not None
                            else None
                        ),
                    ),
                    Interface(
                        type="network",
                        source=f"{self.name}~int",
                        target=f"{self.name}~re{slot}~int",
                        mac=(
                            f"{MAC}:{self.id}:{10 + slot}:01"
                            if self.id is not None
                            else None
                        ),
                    ),
                   Interface(
                       type="network",
                       source=f"{self.name}~res",
                       target=f"{self.name}~re{slot}~res",
                       mac=(
                           f"{MAC}:{self.id}:{10 + slot}:01"
                           if self.id is not None
                           else None
                       ),
                   ),
               ] + [
                    Interface(
                        type=interface.type,
                        source=interface.name,
                        target=f"{self.name}-{10 + slot}-{i}",
                        mac=(
                            f"{MAC}:{self.id}:{10 + slot}:{i}"
                            if self.id is not None
                            else None
                        ),
                    )
                    for i, interface in enumerate(self.interfaces)
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
                    ),
                ],
                interfaces=[
                    Interface(
                        type=self.mgmt.type,
                        source=self.mgmt.name,
                        target=f"{self.name}~fpc{slot}~mgmt",
                        mac=(
                            f"{MAC}:{self.id}:{slot}:0a"
                            if self.id is not None
                            else None
                        ),
                        # model="e1000", # not required in latest junos
                    ),
                    Interface(
                        type="network",
                        source=f"{self.name}~int",
                        target=f"{self.name}~fpc{slot}~int",
                        mac=(
                            f"{MAC}:{self.id}:{slot}:0b"
                            if self.id is not None
                            else None
                        ),
                        # model="e1000", # not required in latest junos
                    ),
                ],
            )
            for slot in [0, ]
        ]

    def vnets(self, vlab: VLab) -> list[VNet]:
        return [
            VNet(name=f"{self.name}~int"),
            VNet(name=f"{self.name}~res"),
        ]

    async def init(self, vlab: VLab):
        return
