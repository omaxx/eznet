from __future__ import annotations

from typing import Iterable, Tuple, Dict, Any

from eznet.verify import Table, calc
from eznet import Inventory, Device

__all__ = ["Interfaces", "Members"]


def interface_state(device: Device, interface_name: str) -> str:
    interfaces_info = device.info.interfaces()
    if interface_name not in interfaces_info:
        return "absent"
    if interfaces_info[interface_name].admin == "down":
        return "disabled"
    return interfaces_info[interface_name].oper or "unknown"


class Members(Table):
    FIELDS = [
        "member",
        "state",
        "info_peer_device",
        "vars_peer_device",
        "info_peer_interface",
        "vars_peer_interface",
    ]

    def __init__(self, inventory: Inventory, device: Device, interface_name: str) -> None:
        def main() -> Iterable[Dict[str, Any]]:
            for member_name, member in device.vars.interfaces[interface_name].members.items():
                yield dict(
                    member=member_name,
                    state=calc(lambda: interface_state(device, member_name), "up"),
                    vars_peer_device=calc(lambda: member.peer.device),
                    # info_peer_device=calc(ref=lambda: member.peer.device),
                    vars_peer_interface=calc(lambda: member.peer.interface),
                    # info_peer_interface=calc(ref=lambda: member.peer.interface),
                )
        super().__init__(main)


class Interfaces(Table):
    FIELDS = [
        "interface",
        # "interface_state",
    ]
    TABLE = Members

    def __init__(self, inventory: Inventory, device: Device):
        def main() -> Iterable[Tuple[Dict[str, Any], Members]]:
            for interface_name, interface in device.vars.interfaces.items():
                yield dict(
                    interface=interface_name,
                    state=calc(lambda: interface_state(device, interface_name), "up"),
                ), Members(inventory, device, interface_name)
        super().__init__(main)


class Alarms(Table):
    FIELDS = [
        "ts",
        "cls",
        "description",
        "type"
    ]

    def __init__(self, inventory: Inventory, device: Device):
        def main() -> Iterable[Dict[str, Any]]:
            for alarm in device.info.system.alarms():
                yield dict(
                    ts=alarm.ts,
                    cls=calc(alarm.cls, ["Major"], lambda v, r: v not in r),
                    description=alarm.description,
                    type=alarm.type,
                )
        super().__init__(main)
