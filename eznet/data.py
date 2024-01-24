from __future__ import annotations

from typing import Generic, TypeVar, Dict, Callable, Awaitable, Any, get_type_hints, Optional, List
from typing_extensions import ParamSpec, Concatenate

import eznet


P = ParamSpec('P')
T = TypeVar('T')
V = TypeVar("V")


class Data(Generic[V]):
    def __init__(
        self,
        func: Callable[Concatenate[eznet.Device, P], Awaitable[Optional[V]]],
        device: eznet.Device,
    ) -> None:
        self.cls = get_type_hints(func)['return']
        self.data: List[V] = []
        self.func = func
        self.device = device

    def __getitem__(self, tag: int) -> V:
        return self.data[tag]

    def __len__(self) -> int:
        return len(self.data)

    # def imp0rt(self, data: Any, tag: str = DEFAULT_TAG) -> None:
    #     self.data[tag] = converter.structure(data, self.cls)
    #

    async def fetch(self, *args: P.args, **kwargs: P.kwargs) -> Optional[V]:
        data = await self.func(self.device, *args, **kwargs)
        if data is not None:
            self.data.insert(0, data)
            return self.data[0]
        return None

    # def exp0rt(self, tag: str = DEFAULT_TAG) -> Any:
    #     data = converter.unstructure(self.data[tag])
    #     return data
