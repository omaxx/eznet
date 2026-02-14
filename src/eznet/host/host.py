from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path

from eznet.drivers import SSH
from eznet.qemu import Qemu

@dataclass
class Host:
    name: str
    ip: str | None = None
    user_name: str | None = None
    user_pass: str | None = None
    root_pass: str | None = None

    def __post_init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

        self.ssh = SSH(
            name=self.name,
            ip=self.ip,
            user_name=self.user_name,
            user_pass=self.user_pass,
            logger=self.logger,
        )

        self.qemu = Qemu(self.ssh)

    async def run(self, cmd: str, stdin: str | None = None):
        await self.ssh.run(cmd, stdin)

    async def mkdir(self, path: str | Path):
        await self.run(f"test -d {path} || mkdir -p {path}")

    async def rmdir(self, path: str | Path):
        await self.run(f"test -d {path} && rm -r {path}")

    async def install(self, *packages: str):
        await self.run("sudo apt-get update")
        for package in packages:
            await self.run(
                f"sudo apt-get install --no-install-recommends -y {package}",
            )

    async def upgrade(self):
        await self.run("sudo apt-get update")
        await self.run("sudo apt-get upgrade -y")

    async def download(self, url: str, path: str | Path):
        await self.mkdir(path)
        await self.run(f"cd {path} && wget --progress=dot:giga {url}")

    async def write_file(
        self,
        file: str | Path,
        content: str,
    ):
        await self.run(f"cat >{file}", stdin=content)
