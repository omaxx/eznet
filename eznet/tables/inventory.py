from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple, Callable

from eznet.table import Table
from eznet import Inventory, Device
from eznet import tables

__all__ = ["DevSummary", "DevInterfaces"]


class DevSummary(Table):
    @dataclass
    class Fields(Table.Fields):
        device: str
        ssh_ip: str
        ssh_error: str
        vars_hostname: str
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
                        ssh_error=self.eval(lambda: device.ssh.error, None),  # type: ignore
                        vars_hostname=self.eval(lambda: device.vars.system.hostname),  # type: ignore
                        info_hostname=self.eval(lambda: device.info.system.info[0].hostname),  # type: ignore
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
