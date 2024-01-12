from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

from eznet.table import Table
from eznet import Inventory, Device

__all__ = ["Interfaces", "Members"]


class Members(Table):
    @dataclass
    class Fields(Table.Fields):
        member: str
        member_state: str

    def __init__(self, inventory: Inventory, device: Device, interface_name: str) -> None:
        def main() -> Iterable[Members.Fields]:
            for member_name, member in device.vars.interfaces[interface_name].members.items():
                yield self.Fields(
                    member=member_name,
                    member_state=self.eval(lambda: device.info.interfaces[0][member_name].state),  # type: ignore
                )
        super().__init__(main)


class Interfaces(Table):
    @dataclass
    class Fields(Table.Fields):
        interface: str
        interface_state: str

    TABLE = Members

    def __init__(self, inventory: Inventory, device: Device):
        def main() -> Iterable[Tuple[Interfaces.Fields, Members]]:
            for interface_name, interface in device.vars.interfaces.items():
                yield self.Fields(
                    interface=interface_name,
                    interface_state=self.eval(lambda: device.info.interfaces[0][interface_name].state),  # type: ignore
                ), Members(inventory, device, interface_name)
        super().__init__(main)
