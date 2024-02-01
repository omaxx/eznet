#!/usr/bin/env python3

from __future__ import annotations

import asyncio
from datetime import datetime
from time import sleep
from typing import Callable, Dict, Any, List, Iterable, Optional, Union, Tuple
import fnmatch
from pathlib import Path
import logging

import click
from rich.console import Console

from eznet import Device, Inventory
from eznet import tables
from eznet.logger import config_logger

JOB_TS_FORMAT = "%Y%m%d-%H%M%S"


@click.command()
@click.option(
    "--inventory", "-i", help="Inventory path", required=True, type=click.types.Path(exists=True),
)
@click.option(
    "--device", "-d", "devices_id", help="device id filter", default=("*",), multiple=True,
)
@click.option(
    "--terminal/--no-terminal", "-t", "force_terminal", help="force terminale", default=None,
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
def run(
    inventory: Union[Inventory, str, Path],
    devices_id: Optional[Tuple[str, ...]],
    force_terminal: Optional[bool] = None,
    width: Optional[int] = None,
    error_if_all: bool = True,
    error_if_any: bool = False,
) -> None:
    console = Console(
        force_terminal=force_terminal,
        width=width,
    )
    config_logger(
        logging.INFO,
        force_terminal=force_terminal,
        width=width,
    )

    if not isinstance(inventory, Inventory):
        inventory = Inventory().load(inventory)

    def device_filter(device: Device) -> bool:
        return devices_id is None or any(fnmatch.fnmatch(device.id, device_id) for device_id in devices_id)

    time_start = datetime.now()
    job_name = time_start.strftime(JOB_TS_FORMAT)
    console.print(f"{job_name}: [black on white]job started at {time_start}")

    async def main() -> None:
        async def process(device: Device) -> None:
            if device.ssh:
                async with device.ssh:
                    await device.info.system.info.fetch()
                    await device.info.system.alarms.fetch()
                    await device.info.system.sw.fetch()
                    await device.info.system.uptime.fetch()
                    await device.info.system.coredumps.fetch()
                    await device.info.interfaces.fetch()

        try:
            errors = [ret is not None for ret in await asyncio.gather(*(
                process(device) for device in inventory.devices if device_filter(device)
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
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print(f"{job_name}: [white on red]keyboard interrupted")
        raise SystemExit(130)
    finally:
        time_stop = datetime.now()
        console.print(f"{job_name}: [black on white]job finished at {time_stop}")


if __name__ == "__main__":
    run()
