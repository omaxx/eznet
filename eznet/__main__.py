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

    def device_filter(device: Device):
        return device_id is None or fnmatch.fnmatch(device.id, device_id)

    async def main(eznet: EZNet) -> None:
        async def process(device: Device) -> None:
            for cmd in [
                "show system info",
                "show system alarms",
            ]:
                await device.junos.run_cmd(cmd)

            for cmd in [
                "show heap",
                "show syslog messages",
            ]:
                await device.junos.run_pfe_cmd(cmd)

            for cmd in [
                "pwd",
                "ls -l",
            ]:
                await device.junos.run_shell_cmd(cmd)

            for cmd in [
                "pwd",
                "ls -l",
            ]:
                await device.junos.run_host_cmd(cmd)

        await eznet.gather(process, device_filter=device_filter)

        eznet.console.print(tables.inventory.DevSummary(eznet.inventory, device_filter=device_filter))
        eznet.console.print(tables.inventory.DevInterfaces(eznet.inventory, device_filter=device_filter))

    try:
        asyncio.run(main(EZNet(inventory)))

    except KeyboardInterrupt:
        raise SystemExit(130)


if __name__ == "__main__":
    run()
