from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from dataclasses import dataclass, field
from pathlib import Path

from eznet.host.config import Config

from eznet.vlab.topology import Node, Link
from eznet.vlab.vm import VM, Disk, Interface

if TYPE_CHECKING:
    from eznet.vlab import VLab

MAC = "ca:ff:ee"

@dataclass(kw_only=True)
class Linux(Node):
    type = "linux"
    image: str
    memory_mb: int = 1024
    vcpus: int = 1
    config: Config | None = None

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
                    Interface(
                        type=interface.type,
                        source=interface.name,
                        target=f"{self.name}-{i}",
                        mac=(
                            f"{MAC}:{self.id}:00:{i}"
                            if self.id is not None
                            else None
                        ),
                    )
                    for i, interface in enumerate(self.interfaces)
                ],
            )
        ]

    async def init(self, vlab: VLab) -> None:
        path = vlab.node_path(node_name=self.name)
        await vlab.host.write_file(path / "meta-data",str(""))
        await vlab.host.write_file(path / "user-data", str(self.config.user_data() or ""))
        await vlab.host.write_file(path / "network-config", str(self.config.network_config() or ""))

        files = ("meta-data", "user-data", "network-config")
        await vlab.host.run(" ".join([
            "genisoimage",
            "-volid cidata",
            "-rational-rock",
            "-joliet",
            "-input-charset utf-8",
            "-quiet",
            f"-output {path}/seed.img",
            " ".join(f"{path}/{file}" for file in files),
        ]))

