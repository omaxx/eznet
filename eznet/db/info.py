from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import ClassVar, TypedDict, Iterable, Dict, List, Tuple

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from attrs import frozen, field

from eznet.device import Device
from .influxdb import Metric


@frozen
class System(Metric):
    MEASUREMENT: ClassVar[str] = "system"

    class Value(Metric.Value):
        hostname: str
        model: str
        junos: str
        serial_number: str

    device: str

    @classmethod
    async def fetch(cls, device: Device) -> Dict[Self, Tuple[datetime, Self.Value]]:
        await device.info.system.info()
        timestamp = datetime.now(timezone.utc)
        return {
            cls(device=device.id): (
                timestamp,
                cls.Value(
                    hostname=device.info.system.info.v.hostname,
                    model=device.info.system.info.v.sw_family,
                    junos=device.info.system.info.v.sw_version,
                    serial_number=device.info.system.info.v.hw_sn,
                ),
            )
        }


@frozen
class JUNOS(Metric):
    MEASUREMENT: ClassVar[str] = "junos"

    class Value(Metric.Value):
        version: str
        product_model: str
        product_name: str

    device: str
    re: str

    @classmethod
    async def fetch(cls, device: Device) -> Dict[Self, Tuple[datetime, Self.Value]]:
        await device.info.system.sw()
        timestamp = datetime.now(timezone.utc)
        return {
            cls(device=device.id, re=re): (
                timestamp,
                cls.Value(
                    version=device.info.system.sw.v[re].junos,
                    product_model=device.info.system.sw.v[re].product_model,
                    product_name=device.info.system.sw.v[re].product_name,
                ),
            )
            for re in device.info.system.sw.v
        }


@frozen
class Firmware(Metric):
    MEASUREMENT: ClassVar[str] = "firmware"

    class Value(dict):
        pass

    device: str
    fpc: str


@frozen
class ChassisRE(Metric):
    MEASUREMENT: ClassVar[str] = "chassis_re"

    class Value(Metric.Value):
        pass

    device: str
    slot: str


@frozen
class ChassisFPC(Metric):
    MEASUREMENT: ClassVar[str] = "chassis_fpc"

    class Value(Metric.Value):
        pass

    device: str
    slot: str


@frozen
class ConnectSSH(Metric):
    BUCKET: ClassVar[str] = "checks"
    MEASUREMENT: ClassVar[str] = "general_connect_ssh"

    class Value(Metric.Value):
        ip: str
        status: str
        error: str

    device: str
