from __future__ import annotations
import asyncio
from typing import Iterable, Tuple, Dict
from dataclasses import dataclass
from rich.console import Console

from eznet import Device, Inventory
from eznet.verify import Table, Check


class MembersTable(Table):
    FIELDS = ["member_name"]

    def __init__(self, inventory: Inventory, device: Device, interface_name: str):
        def main() -> Iterable[Dict[str, str]]:
            interface_data = device.vars.interfaces[interface_name]
            for member_name, member_data in interface_data.members.items():
                yield dict(
                    member_name=member_name,
                )
        super().__init__(main)


class InterfacesTable(Table):
    FIELDS = ["interface_name"]
    TABLE = MembersTable

    def __init__(self, inventory: Inventory, device: Device):
        def main() -> Iterable[Tuple[Dict[str, str], MembersTable]]:
            for interface_name, interface_data in device.vars.interfaces.items():
                yield dict(
                    interface_name=interface_name,
                ), MembersTable(inventory, device, interface_name)
        super().__init__(main)


class DevicesTable(Table):
    FIELDS = ["name"]
    TABLE = InterfacesTable

    def __init__(self, inventory: Inventory):
        def main() -> Iterable[Tuple[Dict[str, str], InterfacesTable]]:
            for device in inventory.devices:
                yield dict(
                    name=device.name,
                ), InterfacesTable(inventory, device)
        super().__init__(main)


class DevicesCheck(Check):
    def __init__(self, inventory: Inventory):
        pass


def cli() -> None:
    console = Console()

    inventory = Inventory().load("inventory/devices.jsonnet")

    devices_table = DevicesTable(inventory)
    # devices_check = DevicesCheck(inventory)

    console.print(devices_table)
    # console.print(devices_check)


if __name__ == "__main__":
    cli()
