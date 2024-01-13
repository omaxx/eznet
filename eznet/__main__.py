#!/usr/bin/env python3

from __future__ import annotations

import asyncio
from time import sleep
from typing import Callable, Dict, Any, List, Iterable, Optional
import fnmatch

import click

from eznet import Device, Inventory
from eznet.application import EZNet
from eznet import tables


@click.command()
@click.option(
    "--inventory", "-i", help="Inventory path", required=True, type=click.types.Path(exists=True),
)
@click.option(
    "--device", "-d", "device_id", help="device filter", default="*",
)
def run(
    inventory: str,
    device_id: Optional[str],
) -> None:
    sleep(1)  # FIXME: workaround for PY-65984

    def device_filter(device: Device) -> bool:
        return device_id is None or fnmatch.fnmatch(device.id, device_id)

    async def main(eznet: EZNet) -> None:
        async def process(device: Device) -> None:
            await device.info.system.info.fetch()
            await device.info.system.alarms.fetch()

        try:
            await eznet.gather(process, device_filter=device_filter)
        except KeyboardInterrupt:
            eznet.console.print("Interrupted!!!")
            raise SystemExit(130)
        finally:
            eznet.console.print(tables.inventory.DevStatus(eznet.inventory, device_filter=device_filter))
            eznet.console.print(tables.inventory.DevAlarms(eznet.inventory, device_filter=device_filter))

    try:
        asyncio.run(main(EZNet(inventory)))

    except KeyboardInterrupt:
        raise SystemExit(130)


if __name__ == "__main__":
    run()
