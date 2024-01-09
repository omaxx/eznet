import asyncio
from typing import Callable, Awaitable, Dict, List, Any
import logging

from rich.console import Console

from .inventory import Inventory, Device
from .logger import config_logger, config_device_logger

MODULE = __name__.split(".")[0]


class EZNet:
    def __init__(
        self,
        inventory: str,
    ):
        self.inventory = Inventory()
        self.inventory.load(inventory)
        self.console = Console()

        config_logger(MODULE, logging.INFO)

    async def gather(
        self,
        process: Callable[[Device], Awaitable[None]],
        device_filter: Callable[[Device], bool] = lambda _: True,
    ) -> None:
        async def _process(device: Device) -> None:
            if device.ssh:
                async with device.ssh:
                    await process(device)

        await asyncio.gather(*(
            _process(device) for device in self.inventory.devices if device_filter(device)
        ), return_exceptions=True)


def call(f: Callable[[], Any]) -> str:
    try:
        return str(f())
    except Exception as err:
        return f"{err.__class__.__name__}: {err}"
