from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple, Callable

from eznet.table import Table
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
                        ssh_ip=self.eval(lambda: device.ssh.ip),  # type: ignore
                        ssh_user=self.eval(lambda: device.ssh.user_name),  # type: ignore
                        ssh_error=self.eval(lambda: device.ssh.error, None),  # type: ignore
                        info_hostname=self.eval(
                            lambda: device.info.system.info[0].hostname,
                            device.name,
                            lambda v, r: r in v,
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
                        hostname=self.eval(lambda: device.info.system.info[0].hostname),  # type: ignore
                        family=self.eval(lambda: device.info.system.info[0].sw_family),  # type: ignore
                        version=self.eval(lambda: device.info.system.info[0].sw_version),  # type: ignore
                        model=self.eval(lambda: device.info.system.info[0].hw_model),  # type: ignore
                        sn=self.eval(lambda: device.info.system.info[0].hw_sn),  # type: ignore

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
