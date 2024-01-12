from typing import Iterable
from dataclasses import dataclass

from eznet.table import Table


def test_create_table():
    class Empty(Table):
        @dataclass
        class Fields(Table.Fields):
            x: int

        def __init__(self, x: int) -> None:
            def main() -> Iterable[Table.Fields]:
                yield self.Fields(
                    x=x,
                )
            super().__init__(main)

    table = Empty(1)
    assert table._rows[0].x == 1
