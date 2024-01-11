from __future__ import annotations

from typing import TypeVar, ClassVar, Generic, List, Dict, Iterable, Callable, Any, Tuple, Type, Optional, Union
from typing_extensions import TypeVarTuple, Self, Unpack, ParamSpec
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, fields, asdict

from rich.table import Table as RTable


P = ParamSpec('P')

NONE = ""


class Table(Generic[P], metaclass=ABCMeta):
    @dataclass
    class Fields:
        pass

    TABLE: ClassVar[Optional[Type[Table[Any]]]] = None

    def __init__(self, *args: P.args, **kwargs: P.kwargs) -> None:
        self._rows = [
            row for row in self.main(*args, **kwargs)
        ]

    @abstractmethod
    def main(self, *args: P.args, **kwargs: P.kwargs) -> Iterable[Union[Fields, Tuple[Fields, Table[Any]]]]:
        pass

    @classmethod
    def fields(cls) -> List[str]:
        return [field.name for field in fields(cls.Fields)]

    @classmethod
    def headers(cls) -> List[str]:
        if cls.TABLE is None:
            return cls.fields()
        else:
            return cls.fields() + cls.TABLE.headers()

    def rows(self):
        for row in self._rows:
            if isinstance(row, Table.Fields):
                yield [asdict(row).get(field, "ERROR") for field in self.fields()]
            elif isinstance(row, tuple):
                yield [asdict(row[0]).get(field, "ERROR") for field in self.fields()]
                for r in row[1].rows():
                    yield [""] * len(self.fields()) + r
            else:
                assert False

    @staticmethod
    def eval(v: Any) -> str:
        try:
            value = v()
            if value is None:
                return NONE
            else:
                return str(value)
        except (AttributeError, IndexError) as err:
            return f"{err.__class__.__name__}"

    def __rich__(self) -> RTable:
        table = RTable(expand=True)
        for header in self.headers():
            table.add_column(header)
        for row in self.rows():
            table.add_row(*row)
        return table
