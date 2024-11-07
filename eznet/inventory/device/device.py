from __future__ import annotations

import logging
from typing import Any, Optional, TypedDict, Union

import marshmallow
import marshmallow_dataclass

from . import info, vars
from .drivers import SSH
from .junos import Junos

IP = Union[str, tuple[str, Optional["Device"]]]


class BaseSchema(marshmallow.Schema):
    class Meta:
        unknown = marshmallow.EXCLUDE


device_vars_schema = marshmallow_dataclass.class_schema(
    vars.Device, base_schema=BaseSchema
)()


class Device(Junos):
    def __init__(
        self,
        name: str,
        ip: Union[IP, list[IP], dict[str, IP], None] = None,
        user_name: Optional[str] = None,
        user_pass: Optional[str] = None,
        root_pass: Optional[str] = None,
        proxy: Optional[Device] = None,
        site: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        self.name = name
        self.site = site
        self.id = self.name if self.site is None else f"{self.site},{self.name}"

        if ip is None:
            self.ip: Union[IP, list[IP], dict[str, IP]] = self.name
        else:
            self.ip = ip
        self.user_name = user_name
        self.user_pass = user_pass
        self.root_pass = root_pass
        self.proxy = proxy.ssh if proxy is not None else None

        self.logger = logging.getLogger(f"eznet.device.{self.name}")

        self.vars: vars.Device = device_vars_schema.load(kwargs)
        self.info = info.Device(self)

        ssh_kwargs_type = TypedDict(
            "ssh_kwargs_type",
            {
                "user_name": Optional[str],
                "user_pass": Optional[str],
                "device_id": str,
            },
        )
        ssh_kwargs: ssh_kwargs_type = dict(
            user_name=user_name,
            user_pass=user_pass,
            device_id=self.id,
        )
        self.ssh_s: dict[Union[str, int], SSH] = {}
        if isinstance(self.ip, str):
            self.ssh_s[0] = SSH(host=self.ip, proxy=self.proxy, **ssh_kwargs)
        elif isinstance(self.ip, tuple):
            self.ssh_s[0] = SSH(
                host=self.ip[0],
                proxy=self.ip[1].ssh if self.ip[1] is not None else None,
                **ssh_kwargs,
            )
        elif isinstance(self.ip, list):
            for i, ip in enumerate(self.ip):
                if isinstance(ip, str):
                    self.ssh_s[i] = SSH(host=ip, proxy=self.proxy, **ssh_kwargs)
                else:
                    self.ssh_s[i] = SSH(
                        host=ip[0],
                        proxy=ip[1].ssh if ip[1] is not None else None,
                        **ssh_kwargs,
                    )
        elif isinstance(self.ip, dict):
            for interface, ip in self.ip.items():
                if isinstance(ip, str):
                    self.ssh_s[interface] = SSH(host=ip, proxy=self.proxy, **ssh_kwargs)
                else:
                    self.ssh_s[interface] = SSH(
                        host=ip[0],
                        proxy=ip[1].ssh if ip[1] is not None else None,
                        **ssh_kwargs,
                    )

    @property
    def ssh(self) -> SSH:
        return list(self.ssh_s.values())[0]

    def __str__(self) -> str:
        return self.id

    def __repr__(self) -> str:
        return f"Device(id={self.id})"
