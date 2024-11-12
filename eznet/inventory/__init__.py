from __future__ import annotations

import logging
from typing import List, Union, Dict, Any, Optional
from typing_extensions import Self
from pathlib import Path
import json
from collections import defaultdict

import yaml
# import _jsonnet

from .device import Device

__all__ = ["Inventory", "Device"]

logger = logging.getLogger(__name__)


class Inventory:
    def __init__(self) -> None:
        self.devices: List[Device] = []

    def device(self, device_id: str) -> Optional[Device]:
        for dev in self.devices:
            if dev.id == device_id:
                return dev
        else:
            return None

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
        # elif path.suffix == ".jsonnet":
        #     logger.info(f"inventory: load from {path}")
        #     try:
        #         self.imp0rt(
        #             json.loads(_jsonnet.evaluate_file(f"{path}")),
        #             site=path.with_suffix("").name,
        #         )
        #     except Exception as exc:
        #         logger.error(f"inventory: load from {path}: {exc.__class__.__name__}: {exc}")
        else:
            logger.error(f"unknown inventory file format {path.suffix[1:]}")

        return self

    def imp0rt(self, data: Dict[str, Any], site: Optional[str] = None) -> None:
        devices: List[Dict[Any, Any]] = data.get("devices", [])
        if not isinstance(devices, list):
            return
        for device_data in devices:
            device_data.setdefault("site", site)
            d = Device(**device_data)
            if d in self.devices:
                logger.error(f"Load error: Duplicate device with {d.id}")
            else:
                self.devices.append(d)

    @property
    def sites(self) -> Dict[Union[str, None], List[Device]]:
        sites: Dict[Union[str, None], List[Device]] = defaultdict(list)
        for d in self.devices:
            sites[d.site].append(d)
        return sites

    def export_as_rundeck(self) -> str:
        return yaml.safe_dump({
            dev.id: {
                "nodename": dev.id,
                **({"hostname": dev.ssh.ip} if dev.ssh is not None else {})
            } for dev in self.devices
        })
