#!/usr/bin/env python3

from __future__ import annotations

import asyncio
from datetime import datetime
from time import sleep
from typing import Callable, Dict, Any, List, Iterable, Optional, Union
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
    "--device", "-d", "devices_id", help="device filter", default=("*",), multiple=True,
)
def run(
    inventory: Union[Inventory, str, Path],
    devices_id: Optional[str],
) -> None:
    sleep(1)  # FIXME: workaround for PY-65984

    console = Console()
    config_logger(logging.INFO)

    if not isinstance(inventory, Inventory):
        inventory = Inventory().load(inventory)

    def device_filter(device: Device) -> bool:
        return devices_id is None or any(fnmatch.fnmatch(device.id, device_id) for device_id in devices_id)

    async def main() -> None:
        async def process(device: Device) -> None:
            if device.ssh:
                async with device.ssh:
                    await device.info.system.info.fetch()
                    await device.info.system.alarms.fetch()

        try:
            await asyncio.gather(*(
                process(device) for device in inventory.devices if device_filter(device)
            ), return_exceptions=True)
        finally:
            console.print()
            console.print(tables.inventory.DevStatus(inventory, device_filter=device_filter))
            console.print(tables.inventory.DevAlarms(inventory, device_filter=device_filter))

    time_start = datetime.now()
    job_name = time_start.strftime(JOB_TS_FORMAT)
    console.print(f"{job_name}: [black on white]job started at {time_start}")
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
