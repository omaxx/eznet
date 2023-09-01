from __future__ import annotations

from typing import List, Dict

from attrs import define
import pytest

import eznet
from eznet.data import Data


@define
class Info:
    value: str

    @classmethod
    async def fetch(cls, _: eznet.device.Device) -> Info:
        return Info(value="single")

    @classmethod
    async def fetch_list(cls, _: eznet.device.Device) -> List[Info]:
        return [
            Info(value="first"),
            Info(value="second"),
        ]

    @classmethod
    async def fetch_dict(cls, _: eznet.device.Device) -> Dict[str, Info]:
        return {
            "first": Info(value="first"),
            "second": Info(value="second"),
        }


class Model:
    def __init__(self) -> None:
        self.info = Data(Info.fetch, eznet.device.Device("test"))
        self.info_list = Data(Info.fetch_list, eznet.device.Device("test"))
        self.info_dict = Data(Info.fetch_dict, eznet.device.Device("test"))


@pytest.mark.asyncio
async def test_fetch():
    model = Model()
    await model.info.fetch("last")
    assert model.info["last"].value == "single"


@pytest.mark.asyncio
async def test_fetch_list():
    model = Model()
    await model.info_list.fetch("last")
    assert model.info_list["last"][0].value == "first"
    assert model.info_list["last"][1].value == "second"


@pytest.mark.asyncio
async def test_fetch_dict():
    model = Model()
    await model.info_dict.fetch("last")
    assert model.info_dict["last"]["first"].value == "first"
    assert model.info_dict["last"]["second"].value == "second"


def test_import():
    model = Model()
    model.info.imp0rt({"value": "single"}, "last")
    assert model.info["last"].value == "single"


def test_import_list():
    model = Model()
    model.info_list.imp0rt([{"value": "first"}, {"value": "second"}], "last")
    assert model.info_list["last"][0].value == "first"
    assert model.info_list["last"][1].value == "second"


def test_import_dict():
    model = Model()
    model.info_dict.imp0rt({"first": {"value": "first"}, "second": {"value": "second"}}, "last")
    assert model.info_dict["last"]["first"].value == "first"
    assert model.info_dict["last"]["second"].value == "second"


def test_export():
    model = Model()
    model.info.data["last"] = Info(value="single")
    assert model.info.exp0rt("last")["value"] == "single"


def test_export_list():
    model = Model()
    model.info_list.data["last"] = [Info(value="first"), Info(value="second")]
    assert model.info_list.exp0rt("last") == [{"value": "first"}, {"value": "second"}]


def test_export_dict():
    model = Model()
    model.info_dict.data["last"] = {"first": Info(value="first"), "second": Info(value="second")}
    assert model.info_dict.exp0rt("last") == {"first": {"value": "first"}, "second": {"value": "second"}}


