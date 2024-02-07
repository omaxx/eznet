import pytest
from dataclasses import dataclass
from eznet.verify import calc, Value, Table, Check


def raise_exception():
    raise Exception()


@pytest.mark.parametrize("test_input, v, status", [
    ({"value": None}, None, None),
    ({"value": lambda: None}, None, None),
    ({"value": 1}, 1, None),
    ({"value": lambda: 1}, 1, None),

    ({"value": raise_exception}, None, Value.Status.NONE),
    ({"value": raise_exception, "ref": 1}, None, Value.Status.NONE),
    ({"value": raise_exception, "ref": None}, None, Value.Status.NONE),
    ({"value": raise_exception, "ref": lambda: 1}, None, Value.Status.NONE),
    ({"value": raise_exception, "ref": lambda: None}, None, Value.Status.NONE),
    ({"value": raise_exception, "ref": raise_exception}, None, Value.Status.NONE),

    ({"value": 1, "ref": 1}, 1, Value.Status.PASS),
    ({"value": lambda: 1, "ref": 1}, 1, Value.Status.PASS),
    ({"value": 1, "ref": lambda: 1}, 1, Value.Status.PASS),
    ({"value": lambda: 1, "ref": lambda: 1}, 1, Value.Status.PASS),

    ({"value": None, "ref": None}, None, Value.Status.PASS),
    ({"value": lambda: None, "ref": None}, None, Value.Status.PASS),
    ({"value": None, "ref": lambda: None}, None, Value.Status.PASS),
    ({"value": lambda: None, "ref": lambda: None}, None, Value.Status.PASS),

    ({"value": 1, "ref": 2, "check": lambda v, r: v < r}, 1, Value.Status.PASS),

    ({"value": 1, "ref": raise_exception}, 1, Value.Status.SKIP),
    ({"value": 1, "ref": raise_exception, "check": lambda v, _: v == 1}, 1, Value.Status.SKIP),

    ({"value": 1, "ref": 2}, 1, Value.Status.FAIL),
    ({"value": 1, "ref": None}, 1, Value.Status.FAIL),
    ({"value": 1, "ref": 1, "check": lambda v, r: v < r}, 1, Value.Status.FAIL),
    ({"value": 1, "ref": None, "check": lambda v, r: v is r}, 1, Value.Status.FAIL),

    ({"value": 1, "check": lambda v, _: v == 1}, 1, Value.Status.PASS),
    ({"value": 1, "check": lambda v, _: v != 1}, 1, Value.Status.FAIL),

    ({"value": 1, "ref": 1, "check": raise_exception}, 1, Value.Status.ERROR),
])
def test_calc_value(test_input, v, status):
    if status is None:
        got = calc(**test_input)
        assert type(got) is type(v)
        assert got == v
    else:
        got = calc(**test_input)
        assert isinstance(got, Value)
        assert got.v == v
        assert got.status == status


@pytest.fixture
def cls_table():
    class _Table(Table):
        FIELDS = ["main"]

        def __init__(self, n: int) -> None:
            def main():
                for i in range(n):
                    yield dict(main=f"m{i}")
            super().__init__(main)

    return _Table


@pytest.fixture
def cls_table_super(cls_table):
    class _Table(Table):
        FIELDS = ["super"]
        TABLE = cls_table

        def __init__(self, n: int) -> None:
            def main():
                for i in range(n):
                    yield dict(main=f"s{i}")
            super().__init__(main)

    return _Table


def test_table(cls_table):
    main_table = cls_table(n=3)
    assert main_table.fields() == ["main"]
    assert main_table.headers() == {"main": "main"}
    # assert list(main_table.rows[0].values()) == [{"main": "m0"}]


def test_check():
    check = Check()
