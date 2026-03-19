from __future__ import annotations

import asyncio
from functools import wraps
from typing import Callable, TypeVar, ParamSpec, Concatenate, Awaitable, Self, Hashable
from abc import ABCMeta

P = ParamSpec("P")
R = TypeVar("R")


class Target(Hashable, metaclass=ABCMeta):
    async def __call__(self, func: Callable[[Self], Awaitable[R]]) -> R:
        result: R = await func(self)
        return result


T = TypeVar("T", bound=Target)


class Group(list[T]):
    def __getitem__(self, predicate: Callable[[T], bool]) -> Self:
        return self.__class__(target for target in self if predicate(target))

    async def __call__(self, func: Callable[[T], Awaitable[R]]) -> dict[T, R | BaseException]:
        results = await asyncio.gather(
            *(target(func) for target in self),
            return_exceptions=True,
        )
        return dict(zip(self, results))


def method(target_cls: type[T], group_cls: type[Group[T]]) -> Callable[
    [Callable[Concatenate[T, P], Awaitable[R]]], Callable[P, Callable[[T], Awaitable[R]]]]:
    def deco(func: Callable[Concatenate[T, P], Awaitable[R]]) -> Callable[P, Callable[[T], Awaitable[R]]]:
        def _func(*args: P.args, **kwargs: P.kwargs) -> Callable[[T], Awaitable[R]]:
            async def _bond(target: T) -> R:
                result = await func(target, *args, **kwargs)
                return result

            return _bond

        @wraps(func)
        async def _target_method(target_self: T, *args: P.args, **kwargs: P.kwargs) -> R:
            return await target_self(_func(*args, **kwargs))

        setattr(target_cls, func.__name__, _target_method)

        @wraps(func)
        async def _group_method(group_self: Group[T], *args: P.args, **kwargs: P.kwargs) -> dict[T, R | BaseException]:
            return await group_self(_func(*args, **kwargs))

        setattr(group_cls, func.__name__, _group_method)

        return _func

    return deco
