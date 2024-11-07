from __future__ import annotations

import sys
from typing import Awaitable, Callable, Generic, NoReturn, TypeVar

if sys.version_info >= (3, 10):
    from typing import Concatenate, ParamSpec
else:
    from typing_extensions import ParamSpec, Concatenate

from datetime import datetime
from xml.etree.ElementTree import Element

P = ParamSpec("P")
T = TypeVar("T")
V = TypeVar("V")


class InfoError(Exception):
    pass


class Info(Generic[T, V, P]):
    def __init__(
        self,
        target: T,
        fetcher: Callable[Concatenate[T, P], Awaitable[V]],
    ):
        self.data: list[tuple[V, datetime]] = []
        self.target = target
        self.fetcher = fetcher

    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> V:
        data = await self.fetcher(self.target, *args, **kwargs)
        self.data.insert(0, (data, datetime.now()))
        return data

    def __getitem__(self, item: int) -> V:
        return self.data[item][0]


def raise_error(xml: Element) -> NoReturn:
    if (output := xml.find("output")) is not None and (
        message := output.text
    ) is not None:
        raise InfoError(message.strip())
    else:
        raise InfoError()
