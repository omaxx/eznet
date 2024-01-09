from dataclasses import dataclass, field

from .system import System


class Device:
    def __init__(self) -> None:
        self.system = System()
