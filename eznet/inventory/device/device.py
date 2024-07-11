from __future__ import annotations

import logging
from typing import Union, Optional, Any, List, Dict

import marshmallow
import marshmallow_dataclass

from . import vars
from . import info
from . import drivers


class BaseSchema(marshmallow.Schema):
    class Meta:
        unknown = marshmallow.EXCLUDE


device_vars_schema = marshmallow_dataclass.class_schema(vars.Device, base_schema=BaseSchema)()


class Device:
    def __init__(
        self,
        name: str,
        site: Optional[str] = None,
        ip: Union[str, List[str], Dict[str, str], None] = None,
        user_name: Optional[str] = None,
        user_pass: Optional[str] = None,
        root_pass: Optional[str] = None,
        proxy: Optional[Device] = None,
        **kwargs: Any,
    ):
        self.name = name
        self.site = site
        self.id = self.name if self.site is None else self.site + "." + self.name
        self.logger = logging.getLogger(f"eznet.device.{self.id}")

        self.vars: vars.Device = device_vars_schema.load(kwargs)
        self.info = info.Device(self)

        self.ssh: Optional[drivers.SSH] = None

        if isinstance(ip, str):
            self.ssh = drivers.SSH(
                ip=ip,
                user_name=user_name,
                user_pass=user_pass,
                proxy=proxy.ssh if proxy is not None and proxy.ssh is not None else None,
                device_id=self.id,
            )
        elif isinstance(ip, list) and len(ip) > 0:
            self.ssh = drivers.SSH(
                ip=ip[0],
                user_name=user_name,
                user_pass=user_pass,
                proxy=proxy.ssh if proxy is not None and proxy.ssh is not None else None,
                device_id=self.id,
            )
        elif isinstance(ip, dict) and len(ip) > 0:
            self.ssh = drivers.SSH(
                list(ip.values())[0],
                user_name=user_name,
                user_pass=user_pass,
                proxy=proxy.ssh if proxy is not None and proxy.ssh is not None else None,
                device_id=self.id,
            )

    def __str__(self) -> str:
        return self.id

    def __repr__(self) -> str:
        return f"Device(id={self.id})"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Device) and self.id == other.id
