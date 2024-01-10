from typing import Iterable
from dataclasses import dataclass

from eznet.table import Table


def test_create_table():
    class Empty(Table[int]):
        @dataclass
        class Fields(Table.Fields):
            x: int

        def main(self, x: int) -> Iterable[Fields]:
            yield self.Fields(
                x=x,
            )

    table = Empty(1)
    assert table.rows[0].x == 1
