from __future__ import annotations

from typing import Literal, TYPE_CHECKING
from dataclasses import dataclass, field

from .vm import VM
from .vnet import VNet

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
class Node:
    name: str
    interfaces: list[Bridge|Network]

    def vms(self, vlab: VLab) -> list[VM]:
        return []

    def vnets(self, vlab: VLab) -> list[VNet]:
        return []

    async def init(self, vlab: VLab) -> None:
        pass


@dataclass
class Topology:
    networks: list[Network] = field(default_factory=list)
    nodes: list[Node] = field(default_factory=list)
