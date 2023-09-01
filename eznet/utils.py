import inspect
from types import FrameType
from typing import Optional, Type, TypeVar

C = TypeVar("C")


def get_caller_object(cls: Type[C], frame: Optional[FrameType] = None) -> Optional[C]:
    frame = frame or inspect.currentframe()
    if frame is None:
        return None

    if "self" in frame.f_locals and isinstance(frame.f_locals["self"], cls):
        return frame.f_locals["self"]
    else:
        frame = frame.f_back
    if frame is None:
        return None
    else:
        return get_caller_object(cls, frame)
