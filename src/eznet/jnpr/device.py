from __future__ import annotations

from dataclasses import dataclass
import logging

from eznet.target import Target, Group, method
from eznet.drivers import SSH


@dataclass
class Device(Target):
    name: str
    ip: str | None = None
    user_name: str | None = None
    user_pass: str | None = None
    root_pass: str | None = None
    proxy: SSH | None = None

    def __post_init__(self) -> None:
        self.id = self.name
        self.logger = logging.getLogger(self.name)

        self.ssh = SSH(
            name=self.name,
            ip=self.ip,
            user_name=self.user_name,
            user_pass=self.user_pass,
            proxy=self.proxy,
            logger=self.logger,
        )

    def __hash__(self) -> int:
        return hash(self.id)


class Devices(Group[Device]):
    pass


device_method = method(Device, Devices)
