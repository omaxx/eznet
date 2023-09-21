from __future__ import annotations

from typing import Generic, TypeVar, Dict, Callable, Awaitable, Any, get_type_hints, Optional
from typing_extensions import ParamSpec, Concatenate

import cattrs

import eznet


DEFAULT_TAG = "default"

converter = cattrs.Converter()

P = ParamSpec('P')
V = TypeVar("V")


class Data(Generic[V]):
    def __init__(
        self,
        func: Callable[Concatenate[eznet.device.Device, P], Awaitable[Optional[V]]],
        device: eznet.device.Device,
    ) -> None:
        self.cls = get_type_hints(func)['return']
        self.data: Dict[str, V] = {}
        self.func = func
        self.device = device

    def __getitem__(self, tag: str) -> V:
        return self.data[tag]

    def imp0rt(self, data: Any, tag: str = DEFAULT_TAG) -> None:
        self.data[tag] = converter.structure(data, self.cls)

    @property
    def v(self) -> Optional[V]:
        return self.data.get(DEFAULT_TAG)

    async def fetch(self, tag: str = DEFAULT_TAG, *args: P.args, **kwargs: P.kwargs) -> Optional[V]:
        data = await self.func(self.device, *args, **kwargs)
        if data is not None:
            self.data[tag] = data
            return self.data[tag]
        return None

    def exp0rt(self, tag: str = DEFAULT_TAG) -> Any:
        data = converter.unstructure(self.data[tag])
        return data
