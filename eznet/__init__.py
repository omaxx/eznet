import logging

from .inventory.device.drivers.ssh import SSH
from .inventory import Inventory, Device
from .logging import create_rich_handler

__all__ = ["Inventory", "Device", "SSH"]


def init() -> None:
    logger = logging.getLogger("eznet")
    logger.setLevel(logging.INFO)
    logger.addHandler(create_rich_handler(logging.INFO))
    logger.info("eznet logging enabled")
