from __future__ import annotations

from eznet.host import Host
from eznet.host.config import user_data, network_config

from .vlab import VLab
from .nodes import Linux, Bridge, Network, vMX

networks = [
    Network("srv1"),
    Network("srv2"),
]

nodes = [
    Linux(
        name = "srv1",
        image="debian-13-genericcloud-amd64.qcow2",
        interfaces=[
            Network("mgmt"), Network("srv1"),
        ],
        user_data=user_data(),
        network_config=network_config("192.168.0.1/24", "192.168.1.1/24")
    ),
    Linux(
        name="srv2",
        image="debian-13-genericcloud-amd64.qcow2",
        interfaces=[
            Network("mgmt"), Network("srv2"),
        ],
        user_data=user_data(),
        network_config=network_config("192.168.0.2/24", "192.168.2.1/24")
    ),
    vMX(
        name="vmx1",
        version="24.4R1-S2.9",
        re_image="junos-vmx-x86-64-24.4R1-S2.9.qcow2",
        fpc_image="vFPC-20241118.img",
        interfaces=[
            Network("srv1"), Network("srv2"),
        ],
    )
]

class App:
    def __init__(self, ip: str = "172.31.0.8"):
        self.host = Host(ip)
        self.vlab = VLab(self.host)

    async def create(self):
        async with self.host.qemu:
            for network in networks:
                await self.vlab.create_network(network)
            for node in nodes:
                await self.vlab.create_node(node)

    async def start(self):
        async with self.host.qemu:
            for network in networks:
                await self.vlab.start_network(network.name)
            for node in nodes:
                await self.vlab.start_node(node.name)

    async def stop(self):
        async with self.host.qemu:
            for node in nodes:
                await self.vlab.stop_node(node.name)
            for network in networks:
                await self.vlab.stop_network(network.name)

    async def delete(self):
        async with self.host.qemu:
            for node in nodes:
                await self.vlab.delete_node(node.name)
            for network in networks:
                await self.vlab.delete_network(network.name)
