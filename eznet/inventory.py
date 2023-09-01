from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

import yaml

from eznet.device import Device

logger = logging.getLogger(__name__)


class Inventory:
    def __init__(self) -> None:
        self.devices: List[Device] = []

    def load(self, path: Union[str, Path]) -> None:
        if isinstance(path, str):
            path = Path(path)
        path = path.expanduser()
        if not path.exists():
            logger.error(f"{path} not found")
        elif path.is_dir():
            logger.info(f"inventory: load from {path}/")
            for child in path.glob("*"):
                if child.is_dir() or child.suffix in [".yaml"]:
                    self.load(child)
        elif path.suffix == ".yaml":
            logger.info(f"inventory: load from {path}")
            with open(path) as io:
                self.imp0rt(
                    yaml.safe_load(io.read()) or {},
                    site=path.with_suffix("").name,
                )
        elif path.suffix == ".json":
            logger.error(f"json is not supported yet")
        elif path.suffix == ".jsonnet":
            logger.error(f"jsonnet is not supported yet")
        else:
            logger.error(f"unknown inventory file format {path.suffix[1:]}")

    def imp0rt(self, data: Dict[str, Any], site: Optional[str] = None) -> None:
        devices: List[Dict[Any, Any]] = data.get("devices", [])
        if not isinstance(devices, list):
            return
        for device_data in devices:
            device_data.setdefault("site", site)
            device = Device(**device_data)
            if device in self.devices:
                logger.error(f"Load error: Duplicate device with {device.id}")
            else:
                self.devices.append(device)
