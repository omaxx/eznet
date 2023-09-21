from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import json

import yaml
import _jsonnet

from eznet.device import Device

logger = logging.getLogger(__name__)


class Inventory:
    def __init__(self) -> None:
        self.devices: List[Device] = []

    def device(self, name: str) -> Optional[Device]:
        for device in self.devices:
            if device.name == name:
                return device
        else:
            return None

    def load(self, path: Union[str, Path]) -> Inventory:
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
            try:
                with open(path) as io:
                    self.imp0rt(
                        yaml.safe_load(io.read()) or {},
                        site=path.with_suffix("").name,
                    )
            except Exception as exc:
                logger.error(f"inventory: load from {path}: {exc.__class__.__name__}: {exc}")
        elif path.suffix == ".json":
            logger.info(f"inventory: load from {path}")
            try:
                with open(path) as io:
                    self.imp0rt(
                        json.loads(io.read()),
                        site=path.with_suffix("").name,
                    )
            except Exception as exc:
                logger.error(f"inventory: load from {path}: {exc.__class__.__name__}: {exc}")
        elif path.suffix == ".jsonnet":
            logger.info(f"inventory: load from {path}")
            try:
                self.imp0rt(
                    json.loads(_jsonnet.evaluate_file(f"{path}")),
                    site=path.with_suffix("").name,
                )
            except Exception as exc:
                logger.error(f"inventory: load from {path}: {exc.__class__.__name__}: {exc}")
        else:
            logger.error(f"unknown inventory file format {path.suffix[1:]}")

        return self

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

    @property
    def sites(self) -> Dict[Union[str, None], List[Device]]:
        sites: Dict[Union[str, None], List[Device]] = {}
        for device in self.devices:
            if device.site not in sites:
                sites[device.site] = []
            sites[device.site].append(device)
        return sites
