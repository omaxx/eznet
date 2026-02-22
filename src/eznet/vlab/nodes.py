from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TYPE_CHECKING

from eznet.qemu.vm import VM, Disk, Interface
from eznet.qemu.vnet import VNet
from eznet.host.config import UserData, NetworkConfig

if TYPE_CHECKING:
    from .vlab import VLab


@dataclass
class Bridge:
    name: str

    @property
    def type(self) -> Literal["bridge"]:
        return "bridge"


@dataclass
class Network:
    name: str

    @property
    def type(self) -> Literal["network"]:
        return "network"

    def vnet(self) -> VNet:
        return VNet(
            name=self.name,
            bridge=self.name,
        )


@dataclass
class Node(ABC):
    name: str
    interfaces: list[Bridge|Network]

    def path(self, vlab: VLab) -> Path:
        return vlab.vms_path / self.name

    @abstractmethod
    def vms(self, vlab: VLab) -> list[VM]:
        return []

    def vnets(self, vlab: VLab) -> list[VNet]:
        return []

    async def init(self, vlab: VLab) -> None:
        pass


@dataclass
class Linux(Node):
    image: str
    vcpus: int = 1
    memory_mb: int = 1024
    user_data: UserData | None = None
    network_config: NetworkConfig | None = None

    async def init(self, vlab: VLab) -> None:
        path = vlab.vms_path / self.name
        await vlab.host.write_file(path / "meta-data",str(""))
        await vlab.host.write_file(path / "user-data", str(self.user_data or ""))
        await vlab.host.write_file(path / "network-config", str(self.network_config or ""))

        files = ("meta-data", "user-data", "network-config")
        await vlab.host.run(" ".join([
            "genisoimage",
            "-volid cidata",
            "-rational-rock",
            "-joliet",
            "-input-charset utf-8",
            f"-output {path}/seed.img",
            " ".join(f"{path}/{file}" for file in files),
        ]))

    def vms(self, vlab: VLab) -> list[VM]:
        images_path = vlab.images_path / "linux"
        return [
            VM(
                name=self.name,
                path=self.path(vlab),
                vcpus=self.vcpus,
                memory_mb=self.memory_mb,
                disks=[
                    Disk(path=images_path / self.image, target="vda", format="qcow2", snapshot=True),
                    Disk(path=Path("seed.img") , target="vdb", format="raw"),
                ],
                interfaces=[
                    Interface(type=interface.type, source=interface.name, target=f"{self.name}-{i}")
                    for i, interface in enumerate(self.interfaces)
                ],
            )
        ]



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
        images_path = vlab.images_path / "junos/vmx" / self.version
        return [
            VM(
                name=f"{self.name}~re{slot}",
                path = self.path(vlab) / f"re{slot}",
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
                    Interface("network", source="mgmt", target=f"{self.name}~re{slot}~mgmt"),
                    Interface("network", source=f"{self.name}~int", target=f"{self.name}~re{slot}~int"),
                ],
            )
            for slot in [0, ]
        ] + [
            VM(
                name=f"{self.name}~fpc{slot}",
                machine="pc",
                path = self.path(vlab) / f"fpc{slot}",
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
                    Interface("network", source="mgmt", target=f"{self.name}~fpc{slot}~mgmt"),
                    Interface("network", source=f"{self.name}~int", target=f"{self.name}~fpc{slot}~int"),
                    Interface("network", source=f"{self.name}~fab", target=f"{self.name}~fpc{slot}~fab"),
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
        for re in ["re0", ]:
            hdd_image = vlab.vms_path / self.name / re / "hdd.img"

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
