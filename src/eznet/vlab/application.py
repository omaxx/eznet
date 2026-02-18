from __future__ import annotations

from eznet.host import Host
from eznet.host.config import user_data, network_config

from .vlab import VLab
from .nodes import Linux, Bridge, Network

nodes = [
    Linux(
        name = "srv-1",
        image="debian-13-genericcloud-amd64.qcow2",
        interfaces=[
            Network("mgmt"), Network("p2p-1"), Network("p2p-2"),
        ],
        user_data=user_data(),
        network_config=network_config("192.168.0.1/24", "192.168.1.1/24", "192.168.2.1/24")
    ),
    Linux(
        name="srv-2",
        image="debian-13-genericcloud-amd64.qcow2",
        interfaces=[
            Network("mgmt"), Network("p2p-1"), Network("p2p-2"),
        ],
        user_data=user_data(),
        network_config=network_config("192.168.0.2/24", "192.168.1.2/24", "192.168.2.2/24")
    ),
]

class App:
    def __init__(self, ip: str = "172.31.0.8"):
        self.host = Host(ip)
        self.vlab = VLab(self.host)

    async def create(self):
        async with self.host.qemu:
            for node in nodes:
                await self.vlab.create(node)

    async def start(self):
        async with self.host.qemu:
            for node in nodes:
                await self.vlab.start(node.name)

    async def stop(self):
        async with self.host.qemu:
            for node in nodes:
                await self.vlab.stop(node.name)

    async def delete(self):
        async with self.host.qemu:
            for node in nodes:
                await self.vlab.delete(node.name)
