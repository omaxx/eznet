from __future__ import annotations

from typing import Iterable, Dict, Callable, Any, no_type_check, Tuple

from rich.console import Console
from eznet.table import Table

from . import Inventory, Device


class Devices(Table[Inventory, Device]):
    fields = ["device", "ssh.ip", "vars.hostname", "info.hostname"]

    def iter(self, inventory: Inventory) -> Iterable[Device]:
        for device in inventory.devices:
            yield device

    @no_type_check
    def row(self, inventory: Inventory, device: Device) -> Dict[str, Callable[[], Any]]:
        return {
            "device": lambda: device.name,
            "ssh.ip": lambda: device.ssh.ip,
            "vars.hostname": lambda: device.vars.system.hostname,
            "info.hostname": lambda: device.info.system.info[0].hostname,
        }


class Interfaces(Table[Inventory, Device, str]):
    fields = ["interface", "interface.state"]

    def iter(self, inventory: Inventory, device: Device) -> Iterable[str]:
        for interface_name in device.vars.interfaces.keys():
            yield interface_name

    @no_type_check
    def row(self, inventory: Inventory, device: Device, interface_name: str) -> Dict[str, Callable[[], Any]]:
        return {
            "interface": lambda: interface_name,
            "interface.state": lambda: device.info.interfaces[0][interface_name].state,
        }


class Members(Table[Inventory, Device, str, str]):
    fields = ["member", "member.state"]

    def iter(self, inventory: Inventory, device: Device, interface_name: str) -> Iterable[str]:
        for member_name in device.vars.interfaces[interface_name].members.keys():
            yield member_name

    @no_type_check
    def row(self, inventory: Inventory, device: Device, interface_name: str, member_name: str) -> Dict[str, Callable[[], Any]]:
        return {
            "member": lambda: member_name,
            "member.state": lambda: device.info.interfaces[0][member_name].state,
        }
