from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Optional, Union

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

import json
from collections import defaultdict

import yaml

try:
    import _jsonnet
    JSONNET = True
except ImportError:
    JSONNET = False

from .device import Device

logger = logging.getLogger("eznet.inventory")


class Inventory:
    def __init__(self) -> None:
        self.devices: dict[str, Device] = {}

    def load(self, path: Union[str, Path]) -> Self:
        if not isinstance(path, Path):
            path = Path(path)
        path = path.expanduser()

        if not path.exists():
            logger.error(f"inventory load error: {path} not found")

        if path.is_dir():
            logger.info(f"inventory: load from {path}/")
            for child in sorted(path.glob("*")):
                if child.is_dir() or child.suffix in [".yaml", ".yml", ".json", ".jsonnet"]:
                    self.load(child)
        elif path.suffix in [".yaml", ".yml"]:
            logger.info(f"inventory: load from {path}")
            try:
                with open(path) as io:
                    self.imp0rt(
                        yaml.safe_load(io.read()) or {},
                        site=path.with_suffix("").name,
                    )
            except Exception as err:
                logger.error(f"inventory: load from {path}: {err.__class__.__name__}: {err}")
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
            if JSONNET:
                logger.info(f"inventory: load from {path}")
                try:
                    self.imp0rt(
                        json.loads(_jsonnet.evaluate_file(f"{path}")),
                        site=path.with_suffix("").name,
                    )
                except Exception as exc:
                    logger.error(f"inventory: load from {path}: {exc.__class__.__name__}: {exc}")
            else:
                logger.error(f"inventory: load from {path}: jsonnet library is not installed")
        else:
            logger.error(f"unknown inventory file format {path.suffix[1:]}")

        return self

    def imp0rt(self, data: dict[str, Any], site: Optional[str] = None) -> None:
        devices: list[dict[Any, Any]] = data.get("devices", [])
        if not isinstance(devices, list):
            return
        for device_data in devices:
            device_data.setdefault("site", site)
            device = Device(**device_data)
            if device.id in self.devices:
                logger.error(f"Load error: Duplicate device with {device.id}")
            else:
                self.devices[device.id] = device

    @property
    def sites(self) -> dict[Union[str, None], dict[str, Device]]:
        sites: dict[Union[str, None], dict[str, Device]] = defaultdict(dict)
        for device_id, device in self.devices.items():
            sites[device.site][device_id] = device
        return sites

    def export_as_rundeck(self) -> str:
        return yaml.safe_dump({
            device.id: {
                "nodename": device.id,
                **({"hostname": device.ssh.host} if device.ssh is not None else {})
            } for device in self.devices.values()
        })
