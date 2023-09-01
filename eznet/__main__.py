#!/usr/bin/env python3

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
import sys
from typing import Optional, Union
from pathlib import Path

import click
from rich import print

from eznet.logger import config_logger, config_device_logger
from eznet.inventory import Inventory
from eznet.device import Device
from eznet.rsi import rsi

JOB_TS_FORMAT = "%Y%m%d-%H%M%S"


def main(
    inventory_path: Union[Path, str],
    jobs_path: Union[Path, str] = "jobs/",
    job_name: Optional[str] = None,
    device_id: Optional[str] = None,
) -> None:
    time_start = datetime.now()

    if not isinstance(jobs_path, Path):
        jobs_path = Path(jobs_path)
    jobs_path.expanduser()
    job_name = job_name or time_start.strftime(JOB_TS_FORMAT)
    job_path = jobs_path / job_name
    config_logger(logging.INFO, job_path / "journal.log")
    print(f"{job_name}: [black on white]job started at {time_start}")
    print(f"{job_name}: job folder: {job_path.absolute()}")

    try:
        inventory = Inventory()
        inventory.load(inventory_path)

        def device_filter(device):
            return device_id is None or device.id == device_id

        async def process(
            device: Device,
        ) -> None:
            config_device_logger(device, logging.DEBUG, file=job_path / f"{device.id}.log")

            async with device.ssh:
                # TODO: print status
                await device.info.system.info()
                await device.info.chassis.re()
                await device.info.chassis.fpc()
                await device.info.system.uptime()

                await rsi(device, job_path=job_path)

            if device.ssh.error is not None:
                # TODO: print error status
                pass

        async def gather() -> None:
            await asyncio.gather(*(
                process(device) for device in inventory.devices if device_filter(device)
            ), return_exceptions=True)

        asyncio.run(gather())
    except KeyboardInterrupt:
        print(f"{job_name}: [red on white]keyboard interrupted")
        sys.exit(130)
    finally:
        time_stop = datetime.now()
        print(f"{job_name}: [black on white]job finished at {time_stop}")
        print(f"{job_name}: job folder: {job_path.absolute()}")


@click.command
@click.option(
    "--inventory", "-i", "inventory_path",
    help="Inventory path", type=click.Path(exists=True),
    default="inventory/devices", show_default=True,
)
@click.option(
    "--jobs", "-j", "jobs_path",
    help="Jobs path", type=click.Path(),
    default="jobs", show_default=True,
)
@click.option(
    "--device-id", "-d", "device_id",
    help="Device filter: id",
)
def cli(
    inventory_path: Optional[str],
    jobs_path: Optional[str],
    device_id: Optional[str],
) -> None:
    main(
        inventory_path=inventory_path,
        jobs_path=jobs_path,
        device_id=device_id,
    )


if __name__ == "__main__":
    cli()
