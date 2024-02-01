from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Tuple

from eznet.table import Table, get
from eznet import Inventory, Device

__all__ = ["Interfaces", "Members"]


def interface_state(device: Device, interface_name: str) -> str:
    interfaces_info = device.info.interfaces()
    if interface_name not in interfaces_info:
        return "absent"
    if interfaces_info[interface_name].admin == "down":
        return "disabled"
    return interfaces_info[interface_name].oper


class Members(Table):
    @dataclass
    class Fields(Table.Fields):
        member: str
        member_state: str
        info_peer_device: str
        vars_peer_device: str
        info_peer_interface: str
        vars_peer_interface: str

    def __init__(self, inventory: Inventory, device: Device, interface_name: str) -> None:
        def main() -> Iterable[Members.Fields]:
            for member_name, member in device.vars.interfaces[interface_name].members.items():
                yield self.Fields(
                    member=member_name,
                    member_state=get(lambda: interface_state(device, member_name), "up"),  # type: ignore
                    vars_peer_device=get(lambda: member.peer.device),
                    info_peer_device=get(ref=lambda: member.peer.device),  # type: ignore
                    vars_peer_interface=get(lambda: member.peer.interface),
                    info_peer_interface=get(ref=lambda: member.peer.interface),  # type: ignore
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
                    interface_state=get(lambda: interface_state(device, interface_name), "up"),  # type: ignore
                ), Members(inventory, device, interface_name)
        super().__init__(main)


class Alarms(Table):
    @dataclass
    class Fields(Table.Fields):
        ts: datetime
        cls: str
        description: str
        type: str

    def __init__(self, inventory: Inventory, device: Device):
        def main() -> Iterable[Alarms.Fields]:
            if not device.info.system.alarms:
                return
            for alarm in device.info.system.alarms():
                yield self.Fields(
                    ts=alarm.ts,
                    cls=get(alarm.cls, ["Major"], lambda v, r: v not in r),
                    description=alarm.description,
                    type=alarm.type,
                )
        super().__init__(main)
