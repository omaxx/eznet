#!/usr/bin/env python3

from __future__ import annotations

import asyncio
from time import sleep
from typing import Callable, Dict, Any, List, Iterable

import click

from eznet import Device, Inventory
from eznet.application import EZNet
from eznet.inventory.tables import Devices, DeviceInterfaces


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

    # await eznet.gather(process)

    eznet.console.print(Devices(eznet.inventory))
    eznet.console.print(DeviceInterfaces(eznet.inventory))


@click.command()
@click.option(
    "--inventory", "-i", required=True,
)
def run(inventory: str) -> None:
    sleep(1)  # FIXME: workaround for PY-65984
    try:
        asyncio.run(main(EZNet(inventory)))

    except KeyboardInterrupt:
        raise SystemExit(130)


if __name__ == "__main__":
    run()
