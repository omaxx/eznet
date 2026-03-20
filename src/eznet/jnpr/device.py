from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Callable, TypeVar, ParamSpec, Concatenate, Awaitable, Any

P = ParamSpec("P")
R = TypeVar("R")


from eznet.target import Target, Group, method
from eznet.drivers import SSH


@dataclass
class Device(Target):
    name: str
    ip: str | None = None
    site: str | None = None
    user_name: str | None = None
    user_pass: str | None = None
    root_pass: str | None = None
    proxy: SSH | None = None

    def __post_init__(self) -> None:
        self.id = self.name if self.site is None else self.site + "." + self.name
        self.logger = logging.getLogger(self.name)

        self.ssh = SSH(
            name=self.name,
            ip=self.ip,
            user_name=self.user_name,
            user_pass=self.user_pass,
            proxy=self.proxy,
            logger=self.logger,
        )

    def __str__(self) -> str:
        return self.id

    def __repr__(self) -> str:
        return f"Device(id=`{self.id}`)"

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Device) and self.id == other.id


class Devices(Group[Device]):
    pass


def device_method(
    prefix: str | None = None,
) -> Callable[[Callable[Concatenate[Device, P], Awaitable[R]]], Callable[P, Callable[[Device], Awaitable[R]]]]:
    return method(Device, Devices)(prefix)
