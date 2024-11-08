from __future__ import annotations

import asyncio
from typing import Union, Optional
from pathlib import Path
import fnmatch
from datetime import datetime
import logging

import click
from rich.console import Console

from eznet import Inventory, Device
from eznet.logging import create_rich_handler
from eznet import tables


@click.command()
@click.option(
    "--inventory", "-i", "inventory_path", help="Inventory path", type=click.types.Path(exists=True),
)
@click.option(
    "--device", "-d", "devices_id", help="device id filter", default=("*",), multiple=True,
)
@click.option(
    "--terminal/--no-terminal", "-t", "force_terminal", help="force terminal", default=None,
)
@click.option(
    "--width", "-w", help="terminal width", type=int,
)
@click.option(
    "--error-if-all/--no-error-if-all", help="exit code 1 if connect error to ALL devices",
    default=True, show_default=True,
)
@click.option(
    "--error-if-any/--no-error-if-any", help="exit code 2 if connect error to ANY device",
    default=False, show_default=True,
)
def cli(
    inventory_path: Union[str, Path],
    devices_id: Optional[tuple[str, ...]],
    force_terminal: Optional[bool] = None,
    width: Optional[int] = None,
    error_if_all: bool = True,
    error_if_any: bool = False,
) -> None:
    console = Console(
        force_terminal=force_terminal,
        width=width,
    )

    logger = logging.getLogger("eznet")
    logger.setLevel(logging.INFO)
    logger.addHandler(create_rich_handler(logging.INFO, width=width, force_terminal=force_terminal))

    inventory = Inventory()
    if inventory_path is not None:
        inventory.load(inventory_path)

    def device_filter(device: Device) -> bool:
        return devices_id is None or any(fnmatch.fnmatch(device.id, device_id) for device_id in devices_id)

    async def process(device: Device) -> None:
        async with device.ssh:
            await device.info.system.info()
            await device.info.system.alarms()

    async def main() -> None:
        try:
            errors = [ret is not None for ret in await asyncio.gather(*(
                process(device) for device in inventory.devices.values() if device_filter(device)
            ), return_exceptions=True)]

            if error_if_all and all(errors):
                raise SystemExit(1)
            if error_if_any and any(errors):
                raise SystemExit(2)

        except KeyboardInterrupt:
            console.print()

        finally:
            console.print(tables.inventory.DevStatus(inventory, device_filter=device_filter))
            console.print(tables.inventory.DevSummary(inventory, device_filter=device_filter))
            console.print(tables.inventory.DevAlarms(inventory, device_filter=device_filter))
            console.print(tables.inventory.DevInterfaces(inventory, device_filter=device_filter))

    try:
        time_start = datetime.now()
        asyncio.run(main())

    except KeyboardInterrupt:
        raise SystemExit(130)

    finally:
        time_stop = datetime.now()


if __name__ == "__main__":
    cli()
