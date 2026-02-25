from __future__ import annotations

from dataclasses import dataclass

PASSWORD = "$6$4Omf4z3n$Vc3Xszvc5c272RNYax1TmIdleeWjSUIILVKKE0Tuf7zI4Z1tjG0j2ueIsXJX5fk3VUAFHItyhTWQRtod318oS."

@dataclass
class Config:
    @dataclass
    class Interface:
        ip: str

    hostname: str
    interfaces: dict[str, Interface]

    def __str__(self):
        return f"""\
system {{
    host-name {self.hostname};
    root-authentication {{
        encrypted-password "{PASSWORD}";
    }}
    syslog {{
        file interactive-commands {{
            interactive-commands any;
        }}
        file messages {{
            any notice;
            authorization info;
        }}
    }}
}}
        """