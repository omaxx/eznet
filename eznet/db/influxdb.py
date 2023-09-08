from __future__ import annotations

import sys
from typing import Optional, ClassVar, TypedDict, List, Tuple, get_type_hints, Dict, Any
from datetime import datetime, timezone

if sys.version_info >= (3, 11):
    from typing import Self, Unpack
else:
    from typing_extensions import Self, Unpack

from attrs import frozen, asdict
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

DEFAULT_TIMEOUT = 60_000

_client: Optional[InfluxDBClient] = None
_org: Optional[str] = None


def init(
    url: str,
    org: str,
    token: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> None:
    global _client
    _client = InfluxDBClient(
        url=url,
        token=token,
        org=org,
        timeout=timeout,
    )
    global _org
    _org = org


def get_client() -> InfluxDBClient:
    if _client is not None:
        return _client
    else:
        raise Exception("InfluxDB is not initialized yet")


@frozen
class Metric:
    BUCKET: ClassVar[str] = "metrics"
    MEASUREMENT: ClassVar[str]

    class Value(TypedDict, total=False):
        pass

    @classmethod
    def tags(cls) -> List[str]:
        return [tag for tag, value in get_type_hints(cls).items() if value == str]

    @classmethod
    def fields(cls) -> Dict[str, Any]:
        return get_type_hints(cls.Value)

    def write(
        self,
        timestamp: datetime,
        **kwargs: Unpack[Value]
    ) -> None:
        for key, value in kwargs.items():
            if key not in self.fields():
                raise TypeError(f"wrong field `{key}`, expected: {list(self.fields().keys())}")
            elif not isinstance(value, self.fields()[key]):
                raise TypeError(f"wrong type for field `{key}`, expected: {self.fields()[key]}")
        get_client().write_api(write_options=SYNCHRONOUS).write(
            bucket=self.BUCKET,
            record={
                "measurement": self.MEASUREMENT,
                "tags": {
                    tag: getattr(self, tag) for tag in self.tags()
                },
                "time": timestamp,
                "fields": kwargs,
            }
        )

    @classmethod
    def get(
        cls,
        time_start: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc),
        time_stop: Optional[datetime] = None,
        first: bool = False,
        last: bool = False,
    ) -> Dict[Self, List[Tuple[datetime, Value]]]:
        if time_stop is None:
            time_stop = datetime.now(timezone.utc)
        return {
            cls(**{tag: table.records[0][tag] for tag in cls.tags()}): [  # noqa
                (
                    row["_time"],
                    {
                        field: value
                        for field in cls.Value.__annotations__
                        if (value := row.values.get(field)) is not None
                    }
                )
                for row in table.records
            ]
            for table in get_client().query_api().query(f'''
                from(bucket: "{cls.BUCKET}")
                |> range(start: {time_start.isoformat()}, stop: {time_stop.isoformat()})
                |> filter(fn: (r) => r["_measurement"] == "{cls.MEASUREMENT}")
                {"|> first()" if first else ""}
                {"|> last()" if last else ""}
                |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
            ''')
        }

    @classmethod
    def get_first(
        cls,
        time_start: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc),
        time_stop: Optional[datetime] = None,
    ) -> Dict[Self, Tuple[datetime, Value]]:
        return {
            metric: value[0]
            for metric, value in cls.get(time_start=time_start, time_stop=time_stop, first=True).items()
            if len(value) == 1
        }

    @classmethod
    def get_last(
        cls,
        time_start: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc),
        time_stop: Optional[datetime] = None,
    ) -> Dict[Self, Tuple[datetime, Value]]:
        return {
            metric: value[0]
            for metric, value in cls.get(time_start=time_start, time_stop=time_stop, last=True).items()
            if len(value) == 1
        }

    def read(
        self,
        time_start: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc),
        time_stop: Optional[datetime] = None,
        first: bool = False,
        last: bool = False,
    ) -> List[Tuple[datetime, Value]]:
        tag_filter = " and ".join([" "] + [f'r["{tag}"] == "{getattr(self, tag)}"' for tag in self.tags()])
        if time_stop is None:
            time_stop = datetime.now(timezone.utc)
        return [
            (
                row["_time"],
                {
                    field: value
                    for field in self.__class__.Value.__annotations__
                    if (value := row.values.get(field)) is not None
                }
            )
            for table in get_client().query_api().query(f'''
                from(bucket: "{self.__class__.BUCKET}")
                |> range(start: {time_start.isoformat()}, stop: {time_stop.isoformat()})
                |> filter(fn: (r) => r["_measurement"] == "{self.__class__.MEASUREMENT}" {tag_filter})
                {"|> first()" if first else ""}
                {"|> last()" if last else ""}
                |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
            ''')
            for row in table.records
        ]

    def read_first(
        self,
        time_start: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc),
        time_stop: Optional[datetime] = None,
    ) -> Optional[Tuple[datetime, Value]]:
        return value[0] if len(
            value := self.read(time_start=time_start, time_stop=time_stop, first=True)) == 1 else None

    def read_last(
        self,
        time_start: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc),
        time_stop: Optional[datetime] = None,
    ) -> Optional[Tuple[datetime, Value]]:
        return value[0] if len(value := self.read(time_start=time_start, time_stop=time_stop, last=True)) == 1 else None

    @classmethod
    def delete(
        cls,
        time_start: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc),
        time_stop: Optional[datetime] = None,
    ):
        if time_stop is None:
            time_stop = datetime.now(timezone.utc)
        get_client().delete_api().delete(
            org=_org,
            bucket=cls.BUCKET,
            start=time_start,
            stop=time_stop,
            predicate=f'_measurement="{cls.MEASUREMENT}"',
        )


@frozen
class Event:
    BUCKET: ClassVar[str] = "events"
    MEASUREMENT: ClassVar[str]

    class Value(TypedDict, total=False):
        pass

    timestamp: datetime
    # FIXME: should be Self.Value, but got "AttributeError: Value"
    value: Event.Value

    def __str__(self) -> str:
        self_as_dict = asdict(self)  # noqa
        timestamp = self_as_dict.pop("timestamp")
        return f"{self_as_dict} @ {timestamp.astimezone()}"

    @classmethod
    def tags(cls) -> List[str]:
        return [tag for tag, value in get_type_hints(cls).items() if value == str]

    @classmethod
    def fields(cls) -> Dict[str, Any]:
        return get_type_hints(cls.Value)

    def write(self):
        self.update(**self.value)

    def update(
        self,
        **kwargs: Unpack[Value]
    ) -> None:
        for key, value in kwargs.items():
            if key not in self.fields():
                raise TypeError(f"wrong field `{key}`, expected: {list(self.fields().keys())}")
            elif not isinstance(value, self.fields()[key]):
                raise TypeError(f"wrong type for field `{key}`, expected: {self.fields()[key]}")
        self.value.update(kwargs)
        get_client().write_api(write_options=SYNCHRONOUS).write(
            bucket=self.__class__.BUCKET,
            record=[
                {
                    "measurement": self.__class__.MEASUREMENT,
                    "tags": {
                        tag: getattr(self, tag) for tag in self.tags()
                    },
                    "time": self.timestamp,
                    "fields": kwargs,
                }
            ]
        )

    @classmethod
    def get(
        cls,
        time_start: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc),
        time_stop: Optional[datetime] = None,
    ) -> List[Self]:
        if time_stop is None:
            time_stop = datetime.now(timezone.utc)
        return sorted(
            [
                cls(
                    **{tag: row.values.get(tag) for tag in cls.tags()},  # noqa
                    timestamp=row["_time"],
                    value={
                        field: value
                        for field in cls.Value.__annotations__
                        if (value := row.values.get(field)) is not None
                    },
                )
                for table in get_client().query_api().query(f'''
                    from(bucket: "{cls.BUCKET}")
                    |> range(start: {time_start.isoformat()}, stop: {time_stop.isoformat()})
                    |> filter(fn: (r) => r["_measurement"] == "{cls.MEASUREMENT}")
                    |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
                ''')
                for row in table.records
            ],
            key=lambda core_dump: core_dump.timestamp,
            # reverse=True,
        )
