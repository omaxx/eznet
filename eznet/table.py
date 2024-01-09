from __future__ import annotations

from typing import TypeVar, TypeVarTuple, ClassVar, Generic, List, Dict, Iterable, Callable, Any, Unpack, Tuple, Type, Self, Optional
from abc import ABCMeta, abstractmethod
from copy import copy

from rich.table import Table as RTable


M = TypeVarTuple('M')
S = TypeVar('S')
S1 = TypeVar('S1')


class Table(Generic[Unpack[M], S], metaclass=ABCMeta):
    fields: ClassVar[List[str]] = []
    NEXT: Optional[Type[Table[Unpack[Tuple[Unpack[M], S]], Any]]] = None

    @classmethod
    def headers(cls) -> List[str]:
        if cls.NEXT is None:
            return [field for field in cls.fields]
        else:
            return [field for field in cls.fields] + cls.NEXT.headers()

    def __init__(self, *m: Unpack[M]) -> None:
        self.rows: List[List[str]] = []
        for s in self.iter(*m):
            row = self.row(*m, s)
            self.rows.append([self.eval(row.get(field)) for field in self.fields])
            if self.NEXT is not None:
                for srow in self.NEXT(*m, s).rows:
                    self.rows.append([""] * len(self.fields) + srow)

    @staticmethod
    def eval(v: Any) -> str:
        try:
            value = v()
            return str(value)
        except (AttributeError, IndexError) as err:
            return f"{err.__class__.__name__}"

    @abstractmethod
    def iter(self, *m: Unpack[M]) -> Iterable[S]:
        ...

    @abstractmethod
    def row(self, *s: Unpack[Tuple[Unpack[M], S]]) -> Dict[str, Callable[[], Any]]:
        ...

    def __rich__(self) -> RTable:
        table = RTable(expand=True)
        for header in self.headers():
            table.add_column(header)
        for row in self.rows:
            table.add_row(*row)
        return table

    @classmethod
    def add(cls, table: Type[Table[Unpack[Tuple[Unpack[M], S]], Any]]) -> Type[Self]:
        _cls = copy(cls)
        _cls.NEXT = table
        return _cls
