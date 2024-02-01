from __future__ import annotations

from typing import Generic, TypeVar, Dict, Callable, Awaitable, Any, get_type_hints, Optional, List, Tuple
from typing_extensions import ParamSpec, Concatenate
from datetime import datetime

P = ParamSpec('P')
T = TypeVar('T')
V = TypeVar("V")


class DataError(Exception):
    pass


class Data(Generic[T, V]):
    def __init__(
        self,
        obj: T,
        fetcher: Callable[Concatenate[T, P], Awaitable[Optional[V]]],
    ) -> None:
        # self.cls = get_type_hints(fetcher)['return']
        self.data: List[Tuple[V, datetime]] = []
        self.obj = obj
        self.fetcher = fetcher

    # def __getitem__(self, tag: int) -> V:
    #     return self.data[tag]
    #
    # def __len__(self) -> int:
    #     return len(self.data)
    #
    def __bool__(self) -> bool:
        return len(self.data) > 0

    def __call__(self, i: int = 0) -> V:
        if len(self.data) > i:
            return self.data[i][0]
        raise DataError()

    @property
    def v(self) -> Optional[V]:
        if len(self.data) > 0:
            return self.data[0][0]
        else:
            return None

    async def fetch(self, *args: P.args, **kwargs: P.kwargs) -> Optional[V]:
        data = await self.fetcher(self.obj, *args, **kwargs)
        if data is not None:
            self.data.insert(0, (data, datetime.now()))
            return self.data[0][0]
        return None

    # def imp0rt(self, data: Any, tag: str = DEFAULT_TAG) -> None:
    #     self.data[tag] = converter.structure(data, self.cls)
    #

    # def exp0rt(self, tag: str = DEFAULT_TAG) -> Any:
    #     data = converter.unstructure(self.data[tag])
    #     return data
