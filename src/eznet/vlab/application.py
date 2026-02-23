from __future__ import annotations

import logging
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

from eznet.host import Host

from .vlab import VLab
from .topology import Topology

console = Console()
logger =  logging.getLogger("eznet")
logger.setLevel(logging.INFO)
handler = RichHandler(
    level=logging.INFO,
    rich_tracebacks=True,       # Pretty tracebacks
    tracebacks_show_locals=True, # Show local vars in tracebacks
    show_time=True,             # Show timestamp
    show_path=True,             # Show file path
    markup=True,                # Enable Rich markup in messages
)

handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
logger.addHandler(handler)


topology = Topology.from_yaml(Path("./topologies/sp/vlab.yaml").read_text())


class App:
    def __init__(self, ip: str = "172.31.0.8"):
        self.host = Host(ip)
        self.vlab = VLab(self.host)

    async def create(self):
        async with self.vlab:
            for network in topology.networks:
                await self.vlab.create_network(network)
            for node in topology.nodes:
                await self.vlab.create_node(node)

    async def start(self):
        async with self.vlab:
            for node in topology.nodes:
                await self.vlab.start_node(node.name)

    async def status(self):
        async with self.vlab:
            for vm in await self.vlab.list_vms():
                console.print(vm)
            for vnet in await self.vlab.list_vnets():
                console.print(vnet)

    async def stop(self):
        async with self.vlab:
            for node in topology.nodes:
                await self.vlab.stop_node(node.name)

    async def delete(self):
        async with self.vlab:
            for node in topology.nodes:
                await self.vlab.delete_node(node.name)
            for network in topology.networks:
                await self.vlab.delete_network(network.name)
