from __future__ import annotations

import logging
from enum import Enum, auto
from typing import TypeVar, Generic, Union, Optional, Callable, Any, List, Iterable, Dict, ClassVar, Type, Tuple

from rich.console import RichCast
from rich.text import Text
from rich.table import Table as RichTable
from rich.tree import Tree as RichTree

logger = logging.getLogger(__name__)

V = TypeVar('V')


class NoInfo(Exception):
    pass


class NoData(Exception):
    pass


class Value(Generic[V]):
    class Status(Enum):
        PASS = auto()
        FAIL = auto()
        NONE = auto()
        NO_INFO = auto()
        NO_DATA = auto()
        SKIP = auto()
        ERROR = auto()

        def __str__(self) -> str:
            return self.name

    STYLE = {
        Status.PASS: "green",
        Status.FAIL: "bold red reverse",
        Status.NONE: "bold red italic",
        Status.NO_INFO: "bold red italic",
        Status.NO_DATA: "italic",
    }

    DEFAULT_STYLE = ""

    def __init__(self, v: Optional[V], status: Status):
        self.v = v
        self.status = status

    def __repr__(self) -> str:
        if self.status in [Value.Status.NONE, Value.Status.NO_INFO, Value.Status.NO_DATA]:
            return f"{self.status}"
        else:
            return f"{self.status}: {self.v}"

    def __rich__(self) -> Text:
        return Text(f"{self}", style=self.STYLE.get(self.status, self.DEFAULT_STYLE))

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Value):
            return self.v == other.v
        else:
            return type(self.v) is type(other) and self.v == other


def calc(
    value: Union[Callable[[], V], V],
    ref: Union[Callable[[], Any], Any] = (),
    check: Optional[Callable[[V, Any], bool]] = None,
) -> Union[V, Value[V]]:
    if callable(value):
        try:
            value = value()
        except NoData:
            return Value(None, Value.Status.NO_DATA)
        except NoInfo:
            return Value(None, Value.Status.NO_INFO)
        except:  # noqa
            return Value(None, Value.Status.NONE)

    if ref == () and check is None:
        return value

    if callable(ref):
        try:
            ref = ref()
        except:  # noqa
            return Value(value, Value.Status.SKIP)

    try:
        check = check or (lambda v, r: v == r)
        return Value(value, (Value.Status.FAIL, Value.Status.PASS)[(check(value, ref))])
    except Exception as err:
        logger.error(f"table: error {err} during validate {check} of {value}, {ref}")
        return Value(value, Value.Status.ERROR)


class Table:
    FIELDS: ClassVar[List[str]] = []
    TABLE: ClassVar[Optional[Type[Table]]] = None

    @classmethod
    def fields(cls) -> List[str]:
        if cls.TABLE is None:
            return [field for field in cls.FIELDS]
        else:
            return [field for field in cls.FIELDS] + cls.TABLE.fields()

    @classmethod
    def headers(cls) -> Dict[str, str]:
        if cls.TABLE is None:
            return {field: field for field in cls.FIELDS}
        else:
            return {**{field: field for field in cls.FIELDS}, **cls.TABLE.headers()}

    def __init__(self, main: Callable[[], Iterable[Union[Dict[str, Any], Tuple[Dict[str, Any], Table]]]]) -> None:
        try:
            self.rows = [
                row for row in main()
            ]
        except:
            self.rows = None

    rows: Optional[List[Union[Dict[str, Any], Tuple[Dict[str, Any], Table]]]] = None

    def values(self) -> Iterable[Dict[str, Any]]:
        if self.rows is None:
            return
        for row in self.rows:
            if isinstance(row, dict):
                # yield {field: row.get(field, "") for field in self.FIELDS}
                yield row
            elif isinstance(row, tuple):
                table: Table
                row, table = row
                if table.rows is not None:
                    # yield {field: row.get(field, "") for field in self.FIELDS}
                    yield row
                    yield from table.values()
                else:
                    yield {
                        **{field: row.get(field, "") for field in self.FIELDS},
                        **{field: Value(v=None, status=Value.Status.NONE) for field in table.fields()}
                    }

            else:
                assert False

    @staticmethod
    def to_rich(
        v: Any,
    ) -> Union[str, RichCast]:
        if isinstance(v, (str, Value)):
            return v
        else:
            return str(v)

    def __rich__(self) -> RichTable:
        fields = self.fields()
        headers = self.headers()
        values = self.values()

        table = RichTable(expand=True)
        for field in fields:
            table.add_column(headers.get(field, field))
        for row in values:
            table.add_row(*(Table.to_rich(row.get(field, "")) for field in fields))

        return table


class Check:
    class Status(Enum):
        PASS = auto()
        FAIL = auto()
        ERROR = auto()
        SKIP = auto()
        SUB_ERROR = auto()
        SUB_FAIL = auto()
        FATAL = auto()

    STYLES = {
        Status.PASS: "green",
        Status.SKIP: "italic",
        Status.FAIL: "bold red",
        Status.SUB_FAIL: "red",
        Status.ERROR: "bold italic red",
        Status.SUB_ERROR: "italic red",
        Status.FATAL: "bold red reverse"
    }

    DEFAULT_STYLE = ""

    status: Status
    sub_checks: List[Check]

    def __rich__(self) -> RichTree:
        table = RichTable.grid(expand=True)
        table.add_column()
        table.add_column(justify="right")
        table.add_row(
            f"{self.__class__}",
            f"{self.status}",
            style=self.STYLES.get(self.status, self.DEFAULT_STYLE)
        )
        tree = RichTree(table)
        for check in self.sub_checks:
            tree.add(check)
        return tree
