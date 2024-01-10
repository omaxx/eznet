from eznet.table import Table


def test_table():
    class Empty(Table[int]):
        fields = ["x"]

        def iter(self):
            yield 1

        def row(self, x):
            return {
                "x": x,
            }
