from __future__ import annotations

import sys
from typing import ClassVar, TypedDict, Literal, List

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from attrs import frozen, field

from eznet.device import Device
from .influxdb import Event


@frozen
class CoreDump(Event):
    MEASUREMENT: ClassVar[str] = "coredump"

    class Value(TypedDict, total=False):
        file: str
        size: str
        ack: bool
        sr: str

    device: str
    re: str
    host: Literal["No", "Yes"]

    @classmethod
    async def fetch(cls, device: Device) -> List[Self]:
        await device.info.system.coredumps()
        return [
            CoreDump(
                device=device.id,
                re=coredump.re,
                host=("No", "Yes")[coredump.host],
                value=dict(
                    file=coredump.name,
                    size=coredump.size,
                ),
                timestamp=coredump.ts,
            )
            for coredump in device.info.system.coredumps.v
        ]
