from enum import Enum, auto


class ConnectError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class RequestError(Exception):
    pass


class State(Enum):
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    WAITING_CONNECT = auto()
    WAITING_RECONNECT = auto()

    def __repr__(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name


