from __future__ import annotations

from dataclasses import dataclass

PASSWORD = "$6$4Omf4z3n$Vc3Xszvc5c272RNYax1TmIdleeWjSUIILVKKE0Tuf7zI4Z1tjG0j2ueIsXJX5fk3VUAFHItyhTWQRtod318oS."
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

    def system(self):
        return {
            "host-name": self.hostname,
            "root-authentication": {
                "encrypted-password": f"\"{PASSWORD}\"",
            },
            "syslog": {
                f"file {file_name}": {facility: severity for facility, severity in file.items()}
                for file_name, file in SYSLOG.items()
            },
        }

    def value(self):
        return {"system": self.system()}

    def __str__(self):
        return "\n".join(to_lines(self.value()))


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
            if isinstance(value, dict) else
            [f"{key} {value};"]
        )
    ]
