from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from eznet.utils import encrypt_password


PASSWORD = encrypt_password("Juniper#123")
SYSLOG = {
    "interactive-commands": {
        "interactive-commands": "any",
    },
    "messages": {
        "any": "notice",
        "authorization": "info",
    },
}


@dataclass
class Config:
    @dataclass
    class Interface:
        ip: str

    hostname: str
    interfaces: dict[str, Interface]
    fpc_slots: list[int] = field(default_factory=lambda: [0])

    def _system(self):
        return {
            "host-name": self.hostname,
            "root-authentication": {
                "encrypted-password": f"\"{PASSWORD}\"",
            },
            "login": {
                f"user {os.getenv("USER")}": {
                    "class": "super-user",
                    "authentication": {
                        "encrypted-password": f"\"{PASSWORD}\"",
                        "ssh-rsa": f"\"{Path("~/.ssh/id_rsa.pub").expanduser().read_text().strip()}\"",
                    },
                },
            },
            "syslog": {
                f"file {file_name}": file_data
                for file_name, file_data in SYSLOG.items()
            },
            "services": {
                "ssh": None,
            },
        }

    def _interfaces(self):
        return {
            interface_name: {
                "unit 0": {
                    "family inet": {
                        "address": interface_data.ip
                    },
                },
            }
            for interface_name, interface_data in self.interfaces.items()
        }

    def _chassis(self):
        return {
            f"fpc {fpc}": {
                "lite-mode": None,
            }
            for fpc in self.fpc_slots
        }

    def _value(self):
        return {
            "system": self._system(),
            "interfaces": self._interfaces(),
            "chassis": self._chassis(),
        }

    def __str__(self):
        return "\n".join(to_lines(self._value()))


PADDING = " " * 4

def indent(key: str, value: list[str]) -> list[str]:
    return [
        key + " {",
        *[f"{PADDING}{line}" for line in value],
        "}",
    ]

def to_lines(data: dict) -> list[str]:
    return [
        line
        for key, value in data.items()
        for line in (
            indent(key, to_lines(value))
            if isinstance(value, dict) else (
                [f"{key} {value};"]
                if value is not None else
                [f"{key};"]
            )

        )
    ]
