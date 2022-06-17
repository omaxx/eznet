from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import yaml

from eznet.utils import list_to_dict

from .device import Device


@dataclass
class Inventory:
    devices: Dict[str, Device]

    @classmethod
    def load(cls, file: str, devices_data_dir: str = None) -> Inventory:
        with open(file) as io:
            data = yaml.safe_load(io)

        if 'devices' in data:
            data['devices'] = list_to_dict(data['devices'], remove_key=False)

            if devices_data_dir is not None:
                for device_name, device in data['devices'].items():
                    data_path = (Path(file).parent / devices_data_dir / device_name).with_suffix('.yaml')
                    if data_path.exists():
                        with open(data_path) as io:
                            device_data = yaml.safe_load(io)
                            device.update(device_data)

        return cls(
            devices={
                device_name: Device(**device) for device_name, device in data.get('devices', {}).items()
            },
        )

    def get_devices_info(self, devices=None, threads=True):
        if devices is None:
            devices = self.devices.keys()
        if threads:
            with ThreadPoolExecutor() as executor:
                [
                    executor.submit(lambda d: d.get_info(), device)
                    for device_name, device in self.devices.items()
                    if device_name in devices
                ]
        else:
            [
                device.get_info()
                for device_name, device in self.devices.items()
                if device_name in devices
            ]
