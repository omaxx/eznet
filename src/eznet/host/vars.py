from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
import os
from pathlib import Path

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
        dhcp4: bool = False
        addresses: list[str] = field(default_factory=list)

    version: Literal[2] = 2
    ethernets: dict[str, Ethernet] = field(default_factory=list)

    def __str__(self) -> str:
        return "#network-config\n" + yaml.safe_dump({"network": self.to_dict()})


@dataclass
class Vars:
    @dataclass
    class Interface:
        ip: str

    interfaces: dict[str, Interface]

    def user_data(self) -> UserData:
        return UserData(
            users=[
                UserData.User(
                    name=os.getenv("USER"),
                    groups=["sudo"],
                    shell="/bin/bash",
                    sudo=['ALL=(ALL) NOPASSWD:ALL'],
                    ssh_authorized_keys=[Path("~/.ssh/id_rsa.pub").expanduser().read_text().strip()],
                )
            ]
        )

    def network_config(self) -> NetworkConfig:
        return NetworkConfig(
            ethernets={
                iface_name: NetworkConfig.Ethernet(addresses=[iface_config.ip])
                for iface_name, iface_config in self.interfaces.items()
            }
        )
