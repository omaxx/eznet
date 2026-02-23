from __future__ import annotations

from typing import Literal, TYPE_CHECKING, Annotated
from dataclasses import dataclass, field

from mashumaro.mixins.yaml import DataClassYAMLMixin
from mashumaro.types import Discriminator, SerializationStrategy

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

class LinkStrategy(SerializationStrategy):
    def serialize(self, value: Bridge | Network) -> dict[str, str]:
        return {value.type: value.name}

    def deserialize(self, value: dict[str, str]) -> Bridge | Network:
        if "bridge" in value:
            return Bridge(value["bridge"])
        if "network" in value:
            return Network(value["network"])
        raise ValueError(f"Unknown interface type: {value}")


Link = Network | Bridge

@dataclass
class Node:
    class Config:
        serialization_strategy = {
            Link: LinkStrategy(),
        }

    name: str
    type: str
    interfaces: list[Link] = field(default_factory=list)

    def vms(self, vlab: VLab) -> list[VM]:
        return []

    def vnets(self, vlab: VLab) -> list[VNet]:
        return []

    async def init(self, vlab: VLab) -> None:
        pass


from .nodes import *

@dataclass
class Topology(DataClassYAMLMixin):
    networks: list[Network] = field(default_factory=list)
    nodes: list[
        Annotated[Node, Discriminator(field="type", include_subtypes=True)]
    ] = field(default_factory=list)
