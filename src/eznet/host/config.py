from __future__ import annotations

from dataclasses import dataclass, field
from mashumaro.mixins.dict import DataClassDictMixin
import yaml

@dataclass
class UserData(DataClassDictMixin):
    @dataclass
    class User:
        name: str
        groups: list[str]
        shell: str
        sudo: list[str]
        ssh_authorized_keys: list[str]

    users: list[User]

    def __str__(self) -> str:
        return "#cloud-config\n" + yaml.safe_dump(self.to_dict())


@dataclass
class NetworkConfig(DataClassDictMixin):
    @dataclass
    class Ethernet:
        dhcp4: bool
        addresses: list[str] = field(default_factory=list)

    version: int = field(init=False, default=2)
    ethernets: dict[str, Ethernet]

    def __str__(self) -> str:
        return "#network-config\n" + yaml.safe_dump({"network": self.to_dict()})
