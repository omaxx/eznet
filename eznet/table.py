from __future__ import annotations

import logging
from typing import TypeVar, ClassVar, Generic, List, Dict, Iterable, Callable, Any, Tuple, Type, Optional, Union
from typing_extensions import TypeVarTuple, Self, Unpack, ParamSpec, Literal
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, fields, asdict
from enum import Enum, auto

from rich.table import Table as RTable
from rich.text import Text

logger = logging.getLogger(__name__)

P = ParamSpec('P')
V = TypeVar('V')


class NO(Enum):
    NE = "NONE"
    

class Value(Generic[V]):
    class Status(Enum):
        PASS = auto()
        FAIL = auto()
        NO_REF = auto()
        NO_DATA = auto()
        NO_VARS = auto()
        NO_INFO = auto()
        VALIDATE_ERROR = auto()

        def __str__(self) -> str:
            return self.name

    STYLE = {
        Status.PASS: "green",
        Status.NO_VARS: "italic",
        Status.NO_INFO: "bold red italic",
        Status.FAIL: "bold red reverse"
    }

    DEFAULT_STYLE = ""

    def __init__(self, v: Union[V, NO], status: Status, ):
        self.v = v
        self.status = status

    def __rich__(self) -> Text:
        if self.v is NO.NE:
            return Text(f"{self.status}", style=self.STYLE.get(self.status, self.DEFAULT_STYLE))
        else:
            return Text(f"{self.status}: {self.v}", style=self.STYLE.get(self.status, self.DEFAULT_STYLE))


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

    def rows(self) -> Iterable[List[str]]:
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
    def eval(
        v: Callable[[], V],
        ref: Optional[Union[Any, Callable[[], Any]]] = NO.NE,
        func: Callable[[V, Any], bool] = lambda v, r: v == r,
    ) -> Union[V, Value[V]]:
        try:
            value = v()
        except AttributeError as err:
            return Value(NO.NE, Value.Status.NO_VARS)
        except IndexError as err:
            return Value(NO.NE, Value.Status.NO_INFO)
        if ref == NO.NE:
            return value
        if callable(ref):
            try:
                ref = ref()
            except (AttributeError, IndexError):
                return Value(value, Value.Status.NO_REF)
        try:
            return Value(value, (Value.Status.FAIL, Value.Status.PASS)[func(value, ref)])
        except Exception as err:
            logger.error(f"table: error {err} during validate {func} of {v}, {ref}")
            return Value(value, Value.Status.VALIDATE_ERROR)

    def __rich__(self) -> RTable:
        table = RTable(expand=True)
        for header in self.headers():
            table.add_column(header)
        for row in self.rows():
            table.add_row(*row)
        return table
