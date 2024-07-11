from enum import Enum, auto


class State(Enum):
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    WAIT_CONNECT = auto()
    WAIT_RECONNECT = auto()

    def __repr__(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name
