from dataclasses import dataclass


@dataclass
class Member:
    pass


@dataclass
class Interface:
    members: dict[str, Member] = None
