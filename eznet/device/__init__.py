from __future__ import annotations

import logging
from typing import Dict, List, Optional, Union, Any

import cattrs

from . import info
from . import vars
from .drivers import JUNOS, SSH

converter = cattrs.Converter()


class Device:
    def __init__(
        self,
        name: str,
        site: Optional[str] = None,
        ip: Union[str, List[str], Dict[str, str], None] = None,
        user_name: Optional[str] = None,
        user_pass: Optional[str] = None,
        root_pass: Optional[str] = None,
        **kwargs,
    ):
        self.name = name
        self.site = site
        self.id = f"{self.site}.{self.name}" if self.site is not None else self.name

        self.ip = ip or name
        self.user_name = user_name
        self.user_pass = user_pass
        self.root_pass = root_pass
        self.kwargs = kwargs

        self.logger = logging.getLogger(f"eznet.device.{self.id}")

        self.vars: Optional[vars.Device] = None

        if isinstance(ip, str):
            ssh_ip = ip
        elif isinstance(ip, list) and len(ip) > 0:
            ssh_ip = ip[0]
        elif isinstance(ip, dict) and len(ip) > 0:
            ssh_ip = list(ip.values())[0]
        else:
            ssh_ip = None

        self.ssh = SSH(
            ip=ssh_ip,
            user_name=user_name,
            user_pass=user_pass,
            device=self.id,
        )
        self.junos = JUNOS(
            ssh=self.ssh,
        )

        self.info = info.Device(self)

    def __str__(self) -> str:
        return self.id

    def __repr__(self) -> str:
        return f"Device(id={self.id})"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Device) and self.id == other.id

    def import_vars(self, **data):
        self.vars = converter.structure(data, vars.Device)
