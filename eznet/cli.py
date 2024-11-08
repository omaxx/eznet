from __future__ import annotations

import asyncio
import fnmatch
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import click
from rich.console import Console

from eznet import Device, Inventory, tables, version
from eznet.logging import create_rich_handler

JOB_TS_FORMAT = "%Y%m%d-%H%M%S"


def print_version(ctx: click.Context, _: click.Option, value: bool) -> None:
    if not value or ctx.resilient_parsing:
        return
    click.echo(f"eznet: {version.__version__}")
    ctx.exit()


@click.command(epilog=f"version: {version.__version__}")
@click.option(
    "--inventory",
    "-i",
    "inventory_path",
    help="Inventory path",
    type=click.types.Path(exists=True),
)
@click.option(
    "--device",
    "-d",
    "devices_id",
    help="device id filter",
    default=("*",),
    multiple=True,
)
@click.option(
    "--terminal/--no-terminal",
    "-t",
    "force_terminal",
    help="force terminal",
    default=None,
)
@click.option(
    "--width",
    "-w",
    help="terminal width",
    type=int,
)
@click.option(
    "--error-if-all/--no-error-if-all",
    help="exit code 1 if connect error to ALL devices",
    default=True,
    show_default=True,
)
@click.option(
    "--error-if-any/--no-error-if-any",
    help="exit code 2 if connect error to ANY device",
    default=False,
    show_default=True,
)
@click.option("-v", "verbose", count=True)
@click.option("--version", "-V", is_flag=True, callback=print_version, expose_value=False, is_eager=True)
@click.pass_context
def cli(
    ctx: click.Context,
    inventory_path: Union[str, Path],
    devices_id: Optional[tuple[str, ...]],
    force_terminal: Optional[bool] = None,
    width: Optional[int] = None,
    error_if_all: bool = True,
    error_if_any: bool = False,
    verbose: int = 0,
) -> None:
    ctx.ensure_object(dict)
    console = Console(
        force_terminal=force_terminal,
        width=width,
    )

    logger = logging.getLogger("eznet")
    logging_level = (logging.WARNING, logging.INFO, logging.DEBUG)[min(verbose, 2)]
    logger.setLevel(logging_level)
    logger.addHandler(create_rich_handler(logging_level, width=width, force_terminal=force_terminal))

    inventory = Inventory()
    if inventory_path is not None:
        inventory.load(inventory_path)

    def device_filter(device: Device) -> bool:
        return devices_id is None or any(fnmatch.fnmatch(device.id, device_id) for device_id in devices_id)

    async def process(device: Device) -> None:
        async with device.ssh:
            await device.info.system.info.fetch()
            await device.info.system.alarms.fetch()
            await device.info.system.sw.fetch()
            await device.info.system.uptime.fetch()
            await device.info.system.coredumps.fetch()
            await device.info.interfaces.fetch()

    async def main() -> None:
        try:
            errors = [
                ret is not None
                for ret in await asyncio.gather(
                    *(process(device) for device in inventory.devices if device_filter(device)), return_exceptions=True
                )
            ]

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
    cli()
