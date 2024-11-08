from __future__ import annotations

from typing import Any, Callable, Iterable

from eznet import Device, Inventory, tables
from eznet.table import Table, calc

__all__ = ["DevStatus", "DevInterfaces"]


class DevStatus(Table):
    FIELDS = [
        "device",
        "ssh_ip",
        "ssh_user",
        "ssh_error",
        "info_hostname",
    ]

    def __init__(
        self,
        inventory: Inventory,
        device_filter: Callable[[Device], bool] = lambda _: True,
    ) -> None:
        def main() -> Iterable[dict[str, Any]]:
            for device in inventory.devices:
                if device_filter(device):
                    yield dict(
                        device=device.id,
                        ssh_ip=calc(lambda: device.ssh.host),
                        ssh_user=calc(lambda: device.ssh.user_name),
                        ssh_error=calc(lambda: device.ssh.error, None),
                        info_hostname=calc(
                            lambda: device.info.system.info().hostname,
                            device.name,
                            lambda v, r: r.lower() in v.lower(),
                        ),
                    )

        super().__init__(main)


class DevSummary(Table):
    FIELDS = [
        "device",
        "hostname",
        "family",
        "version",
        "model",
        "sn",
    ]

    def __init__(
        self,
        inventory: Inventory,
        device_filter: Callable[[Device], bool] = lambda _: True,
    ) -> None:
        def main() -> Iterable[dict[str, Any]]:
            for device in inventory.devices:
                if device_filter(device):
                    yield dict(
                        device=device.id,
                        hostname=calc(lambda: device.info.system.info().hostname),
                        family=calc(lambda: device.info.system.info().sw_family),
                        version=calc(lambda: device.info.system.info().sw_version),
                        model=calc(lambda: device.info.system.info().hw_model),
                        sn=calc(lambda: device.info.system.info().hw_sn),
                    )

        super().__init__(main)


class DevInterfaces(Table):
    FIELDS = [
        "device",
    ]
    TABLE = tables.device.Interfaces

    def __init__(
        self,
        inventory: Inventory,
        device_filter: Callable[[Device], bool] = lambda _: True,
    ) -> None:
        def main() -> Iterable[tuple[dict[str, Any], Table]]:
            for device in inventory.devices:
                if device_filter(device):
                    yield dict(
                        device=device.id,
                    ), tables.device.Interfaces(inventory, device)

        super().__init__(main)


class DevAlarms(Table):
    FIELDS = [
        "device",
    ]
    TABLE = tables.device.Alarms

    def __init__(
        self,
        inventory: Inventory,
        device_filter: Callable[[Device], bool] = lambda _: True,
    ) -> None:
        def main() -> Iterable[tuple[dict[str, Any], Table]]:
            for device in inventory.devices:
                if device_filter(device):
                    yield dict(
                        device=device.id,
                    ), tables.device.Alarms(inventory, device)

        super().__init__(main)
