from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple, Callable

from eznet.table import Table, get
from eznet import Inventory, Device
from eznet import tables

__all__ = ["DevStatus", "DevInterfaces"]


class DevStatus(Table):
    @dataclass
    class Fields(Table.Fields):
        device: str
        ssh_ip: str
        ssh_user: str
        ssh_error: str
        info_hostname: str

    def __init__(
        self,
        inventory: Inventory,
        device_filter: Callable[[Device], bool] = lambda _: True,
    ) -> None:
        def main() -> Iterable[Table.Fields]:
            for device in inventory.devices:
                if device_filter(device):
                    yield self.Fields(
                        device=device.id,
                        ssh_ip=get(lambda: device.ssh.ip),  # type: ignore
                        ssh_user=get(lambda: device.ssh.user_name),  # type: ignore
                        ssh_error=get(lambda: device.ssh.error, None),  # type: ignore
                        info_hostname=get(
                            lambda: device.info.system.info().hostname,
                            device.name,
                            lambda v, r: r.lower() in v.lower(),
                        ),  # type: ignore
                    )
        super().__init__(main)


class DevSummary(Table):
    @dataclass
    class Fields(Table.Fields):
        device: str
        hostname: str
        family: str
        version: str
        model: str
        sn: str

    def __init__(
        self,
        inventory: Inventory,
        device_filter: Callable[[Device], bool] = lambda _: True,
    ) -> None:
        def main() -> Iterable[Table.Fields]:
            for device in inventory.devices:
                if device_filter(device):
                    yield self.Fields(
                        device=device.id,
                        hostname=get(lambda: device.info.system.info().hostname),  # type: ignore
                        family=get(lambda: device.info.system.info().sw_family),  # type: ignore
                        version=get(lambda: device.info.system.info().sw_version),  # type: ignore
                        model=get(lambda: device.info.system.info().hw_model),  # type: ignore
                        sn=get(lambda: device.info.system.info().hw_sn),  # type: ignore

                    )
        super().__init__(main)


class DevInterfaces(Table):
    @dataclass
    class Fields(Table.Fields):
        device: str

    TABLE = tables.device.Interfaces

    def __init__(
        self,
        inventory: Inventory,
        device_filter: Callable[[Device], bool] = lambda _: True,
    ) -> None:
        def main() -> Iterable[Tuple[Table.Fields, Table]]:
            for device in inventory.devices:
                if device_filter(device):
                    yield self.Fields(
                        device=device.id,
                    ), tables.device.Interfaces(inventory, device)
        super().__init__(main)


class DevAlarms(Table):
    @dataclass
    class Fields(Table.Fields):
        device: str

    TABLE = tables.device.Alarms

    def __init__(
        self,
        inventory: Inventory,
        device_filter: Callable[[Device], bool] = lambda _: True,
    ) -> None:
        def main() -> Iterable[Tuple[Table.Fields, Table]]:
            for device in inventory.devices:
                if device_filter(device):
                    yield self.Fields(
                        device=device.id,
                    ), tables.device.Alarms(inventory, device)
        super().__init__(main)
