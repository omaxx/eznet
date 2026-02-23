from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from dataclasses import dataclass, field
from pathlib import Path

from eznet.host.config import UserData, NetworkConfig

from eznet.vlab.topology import Node
from eznet.vlab.vm import VM, Disk, Interface

if TYPE_CHECKING:
    from eznet.vlab import VLab


@dataclass(kw_only=True)
class Linux(Node):
    type: Literal["linux"] = "linux"
    image: str
    memory_mb: int = 1024
    vcpus: int = 1
    user_data: UserData | None = None
    network_config: NetworkConfig | None = None

    def vms(self, vlab: VLab) -> list[VM]:
        path = vlab.node_path(node_name=self.name)
        images_path = vlab.images_path / "linux"
        return [
            VM(
                name=self.name,
                path=path,
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

    async def init(self, vlab: VLab) -> None:
        path = vlab.node_path(node_name=self.name)
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

