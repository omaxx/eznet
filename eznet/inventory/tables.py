from __future__ import annotations

from typing import Iterable, Dict, Callable, Any, no_type_check, Tuple
from dataclasses import dataclass

from rich.console import Console
from eznet.table import Table

from . import Inventory, Device


class Devices(Table[Inventory]):
    @dataclass
    class Fields(Table.Fields):
        device: str
        ssh_ip: str
        ssh_error: str
        vars_hostname: str
        info_hostname: str

    def main(self, inventory: Inventory) -> Iterable[Fields]:
        for device in inventory.devices:
            yield self.Fields(
                device=device.id,
                ssh_ip=self.eval(lambda: device.ssh.ip),  # type: ignore
                ssh_error=self.eval(lambda: device.ssh.error, None),  # type: ignore
                vars_hostname=self.eval(lambda: device.vars.system.hostname),  # type: ignore
                info_hostname=self.eval(lambda: device.info.system.info[0].hostname),  # type: ignore
            )


class Members(Table[Inventory, Device, str]):
    @dataclass
    class Fields(Table.Fields):
        member: str
        member_state: str

    def main(self, inventory: Inventory, device: Device, interface_name: str) -> Iterable[Fields]:
        for member_name, member in device.vars.interfaces[interface_name].members.items():
            yield self.Fields(
                member=member_name,
                member_state=self.eval(lambda: device.info.interfaces[0][member_name].state),  # type: ignore
            )


class Interfaces(Table[Inventory, Device]):
    @dataclass
    class Fields(Table.Fields):
        interface: str
        interface_state: str

    TABLE = Members

    def main(self, inventory: Inventory, device: Device) -> Iterable[Tuple[Fields, Members]]:
        for interface_name, interface in device.vars.interfaces.items():
            yield self.Fields(
                interface=interface_name,
                interface_state=self.eval(lambda: device.info.interfaces[0][interface_name].state),  # type: ignore
            ), Members(inventory, device, interface_name)


class DeviceInterfaces(Table[Inventory]):
    @dataclass
    class Fields(Table.Fields):
        device: str

    TABLE = Interfaces

    def main(self, inventory: Inventory) -> Iterable[Tuple[Fields, Interfaces]]:
        for device in inventory.devices:
            yield self.Fields(
                device=device.id,
            ), Interfaces(inventory, device)


