from __future__ import annotations

from typing import TypeVar, Generic, Any, ClassVar, Self
from subprocess import run
from pathlib import Path
import json
import yaml
import _jsonnet
from mashumaro.mixins.dict import DataClassDictMixin

T = TypeVar("T", bound="SingletonBase")


def encrypt_password(password: str) -> str:
    result = run(f"openssl passwd -6 {password}", shell=True, capture_output=True)
    if result.returncode == 0:
        return result.stdout.strip().decode("ascii")
    else:
        raise Exception(result.stderr.decode("ascii"))


class MetaSingleton(type):
    instance: SingletonBase | None = None

    def __init__(cls, name: str, bases: tuple[type, ...], ns: dict[str, Any]) -> None:
        super().__init__(name, bases, ns)
        cls.instance = None

    def __call__(cls: type[T], *args: Any, **kwargs: Any) -> T:
        if cls.instance is None:
            cls.instance = super().__call__(*args, **kwargs)  # type: ignore
        return cls.instance  # type: ignore[return-value]

    def get(cls: type[T]) -> T:
        return cls.instance or cls()  # type: ignore[return-value]


class SingletonBase(metaclass=MetaSingleton):
    pass


class Singleton:
    instance = None

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = super().__new__(cls, *args, **kwargs)

        return cls.instance

    @classmethod
    def get(cls):
        return cls.instance or cls()


class DataClassLoadMixin(DataClassDictMixin):
    @classmethod
    def load(cls, path: str | Path) -> Self:
        path = Path(path).expanduser()
        match path.suffix:
            case ".yaml" | ".yml":
                data = yaml.safe_load(path.read_text())
            case ".json":
                data = json.loads(path.read_text())
            case ".jsonnet":
                data = json.loads(_jsonnet.evaluate_file(str(path)))
            case _:
                raise ValueError(f"Unsupported file format: {path.suffix}")
        return cls.from_dict(data)
