from __future__ import annotations

from typing import TypeVar, ClassVar, Generic, List, Dict, Iterable, Callable, Any, Tuple, Type, Optional, Union
from typing_extensions import TypeVarTuple, Self, Unpack, ParamSpec
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass

from rich.table import Table as RTable


P = ParamSpec('P')


class Table(Generic[P], metaclass=ABCMeta):
    @dataclass
    class Fields:
        pass

    @abstractmethod
    def main(self, *args: P.args, **kwargs: P.kwargs) -> Iterable[Union[Fields, Tuple[Fields, Table[Any]]]]:
        pass

    @classmethod
    def headers(cls) -> Iterable[str]:
        return []

    def __init__(self, *args: P.args, **kwargs: P.kwargs) -> None:
        self.rows = [
            row for row in self.main(*args, **kwargs)
        ]

    @staticmethod
    def eval(v: Any) -> str:
        try:
            value = v()
            return str(value)
        except (AttributeError, IndexError) as err:
            return f"{err.__class__.__name__}"

    def __rich__(self) -> RTable:
        table = RTable(expand=True)
        # for header in self.headers():
        #     table.add_column(header)
        # for row in self.rows:
        #     table.add_row(*row)
        return table
