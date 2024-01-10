from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Generic, TypeVar, ClassVar, Optional, Any, List, Callable, Type
from typing_extensions import TypeVarTuple, ParamSpec
from enum import Enum, auto
import functools

from rich.tree import Tree
from rich.table import Table as RTable

from eznet.utils import get_caller_object


class Skip(Exception):
    pass


class Error(Exception):
    pass


class Fail(Exception):
    pass


class Status(Enum):
    PASS = auto()
    FAIL = auto()
    ERROR = auto()
    SKIP = auto()
    SUB_ERROR = auto()
    SUB_FAIL = auto()
    FATAL = auto()

    def __repr__(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name


STYLES = {
    Status.PASS: "green",
    Status.SKIP: "italic",
    Status.FAIL: "bold red",
    Status.SUB_FAIL: "red",
    Status.ERROR: "bold italic red",
    Status.SUB_ERROR: "italic red",
    Status.FATAL: "bold red reverse"
}
DEFAULT_STYLE = "white"

M = TypeVarTuple('M')
P = ParamSpec("P")
C = TypeVar('C', bound="Check[Any]")


class Check(Generic[P], metaclass=ABCMeta):
    name: ClassVar[Optional[str]] = None

    @abstractmethod
    def main(self, *args: P.args, **kwargs: P.kwargs) -> Optional[bool]:
        ...

    def __init__(self, *args: P.args, **kwargs: P.kwargs) -> None:
        self.args = args
        self.kwargs = kwargs

        self.status: Status
        self.error: Optional[str] = None
        self.sub_checks: List[Check[Any]] = []

        try:
            self.main(*args, **kwargs)
        except Skip as err:
            self.status = Status.SKIP
            self.error = f"{err}"
        except Error as err:
            self.status = Status.ERROR
            self.error = f"{err}"
        except Fail as err:
            self.status = Status.FAIL
            self.error = f"{err}"
        except Exception as err:
            self.status = Status.FATAL
            self.error = f"{err.__class__.__name__}: {err}"
        else:
            if any(check.status in [Status.ERROR, Status.SUB_ERROR, Status.FAIL] for check in self.sub_checks):
                self.status = Status.SUB_ERROR
            elif any(check.status in [Status.FAIL, Status.SUB_FAIL] for check in self.sub_checks):
                self.status = Status.SUB_FAIL
            else:
                self.status = Status.PASS

    def verify(self, check: C) -> C:
        self.sub_checks.append(check)
        return check

    def __bool__(self) -> bool:
        return self.status in [Status.PASS]

    def __repr__(self) -> str:
        return f"{self.name or self.__class__.__name__} {self.args} {self.kwargs} --> {self.status}"

    def __rich__(self) -> Tree:
        table = RTable.grid(expand=True)
        table.add_column()
        table.add_column(justify="right")
        table.add_row(
            f"{self.name or self.__class__.__name__} {self.args} {self.kwargs}"
            f"{self.status}{'' if self.error is None else ': ' + self.error}",
            style=STYLES.get(self.status, DEFAULT_STYLE)
        )
        tree = Tree(table)
        for check in self.sub_checks:
            if check.status in [Status.PASS, Status.SKIP]:
                continue
            tree.add(check)
        return tree


# def define_check(func: Callable[P, Optional[bool]]) -> Callable[P, Check[P]]:
def define_check(func: Callable[P, Optional[bool]]) -> Type[Check[P]]:
    class _Check(Check[P]):
        name = func.__name__

        def main(self, *args: P.args, **kwargs: P.kwargs) -> Optional[bool]:
            return func(*args, **kwargs)

    # @functools.wraps(func)
    # def create_ckeck(*args: P.args, **kwargs: P.kwargs) -> _Check:
    #     return _Check(*args, **kwargs)
    #
    # return create_ckeck
    return _Check


def verify(check: C) -> C:
    current_check: Optional[Check[Any]] = get_caller_object(Check)  # type: ignore[type-abstract]
    if current_check is not None:
        return current_check.verify(check)
    else:
        return check
