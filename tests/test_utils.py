from eznet.utils import string_to_dict, list_to_dict


def test_string_to_dict():
    assert string_to_dict("first") == {"name": "first"}
    assert string_to_dict("one", key="number") == {"number": "one"}


def test_list_to_dict():
    assert list_to_dict(["one", "two", "three"]) == {"one": {}, "two": {}, "three": {}}
    assert list_to_dict([{"name": "one"}, {"name": "two"}, {"name": "three"}]) == {"one": {}, "two": {}, "three": {}}
    assert list_to_dict([
        {"name": "one", "color": "red"},
        {"name": "two", "color": "green"},
        {"name": "three", "color": "blue"},
    ]) == {"one": {"color": "red"}, "two": {"color": "green"}, "three": {"color": "blue"}}
    assert list_to_dict([
        {"name": "one", "color": "red"},
        {"name": "two", "color": "green"},
        {"name": "three", "color": "blue"},
    ], remove_key=False) == {
        "one": {"name": "one", "color": "red"},
        "two": {"name": "two", "color": "green"},
        "three": {"name": "three", "color": "blue"},
    }


