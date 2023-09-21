#!/usr/bin/env python3

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
import sys
from typing import Optional, Union, Tuple
from pathlib import Path

import click
from rich import print

from eznet.logger import config_logger, config_device_logger
from eznet.inventory import Inventory
from eznet.device import Device
from eznet.rsi import rsi

JOB_TS_FORMAT = "%Y%m%d-%H%M%S"


def set_path(
    work_path: Union[Path, str],
    jobs_path: Union[Path, str],
    job_name: str,
) -> Tuple[Path, Path, Path, Path]:
    if isinstance(work_path, str):
        work_path = Path(work_path)
    work_path.expanduser()

    if isinstance(jobs_path, str):
        jobs_path = Path(jobs_path)
    jobs_path.expanduser()
    jobs_path = work_path / jobs_path

    job_path = jobs_path / job_name
    log_file = jobs_path / f"{job_name}.log"

    return work_path, jobs_path, job_path, log_file


def main(
    inventory_path: Union[Path, str],
    work_path: Union[Path, str] = "working",
    jobs_path: Union[Path, str] = "jobs",
    job_name: Optional[str] = None,
    device_id: Optional[str] = None,
) -> None:
    time_start = datetime.now()
    job_name = job_name or time_start.strftime(JOB_TS_FORMAT)
    print(f"{job_name}: [black on white]job started at {time_start}")

    work_path, jobs_path, job_path, log_file = set_path(work_path, jobs_path, job_name)
    config_logger(logging.INFO, log_file)
    print(f"{job_name}: [black on white]log file: {log_file.absolute()}, job folder: {job_path.absolute()}")

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
                await device.info.system.info.fetch()
                await device.info.chassis.re.fetch()
                await device.info.chassis.fpc.fetch()
                await device.info.system.uptime.fetch()

                await rsi(device, job_path=job_path)

            if device.ssh.error is not None:
                # TODO: print error status
                pass

        async def gather() -> None:
            await asyncio.gather(*(
                process(device) for device in inventory.devices if device_filter(device)
            ), return_exceptions=False)

        asyncio.run(gather())
    except KeyboardInterrupt:
        print(f"{job_name}: [white on red]keyboard interrupted")
        sys.exit(130)
    finally:
        time_stop = datetime.now()
        print(f"{job_name}: [black on white]job finished at {time_stop}")
        print(f"{job_name}: [black on white]log file: {log_file.absolute()}, job folder: {job_path.absolute()}")


@click.command
@click.option(
    "--inventory", "-i", "inventory_path",
    help="Inventory path", type=click.Path(exists=True),
    default="inventory/devices", show_default=True,
)
@click.option(
    "--work", "-w", "work_path",
    help="Working path", type=click.Path(),
    default="working", show_default=True,
)
@click.option(
    "--jobs", "-j", "jobs_path",
    help="Jobs path (absolute or related to working path)", type=click.Path(),
    default="jobs", show_default=True,
)
@click.option(
    "--device-id", "-d", "device_id",
    help="Device filter: id",
)
def cli(**kwargs) -> None:
    main(**kwargs)


if __name__ == "__main__":
    cli()
