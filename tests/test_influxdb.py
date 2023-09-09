from typing import ClassVar

from datetime import datetime, timedelta, timezone
import uuid

from attrs import frozen, field
from eznet.db.influxdb import init, Metric, Event

init(
    url="http://172.31.0.33:8086",
    org="lab",
    token="nx0_oCl5srcJNyS7lQiea9FJYhfDrpTniiZpY1AsDeCh1iQGCQqxbA9Ox-_pZYfG-CMFA0xrY3ed1Xm3xAB-OA==",
)


@frozen
class CustomMetric(Metric):
    MEASUREMENT: ClassVar[str] = "custom_metric"

    class Value(Metric.Value):
        value: str
    
    tag: str


@frozen
class CustomEvent(Event):
    MEASUREMENT: ClassVar[str] = "custom_event"

    class Value(Event.Value):
        value: str

    tag: str
    value: Value


def test_metric_write():
    now = datetime.now(timezone.utc)
    CustomMetric(tag="one").write(now, value="one")


def test_metrics_get():
    now = datetime.now(timezone.utc)
    value1 = uuid.uuid4().__str__()
    value2 = uuid.uuid4().__str__()
    CustomMetric(tag="one").write(now, value=value1)
    CustomMetric(tag="two").write(now, value=value2)
    metrics = CustomMetric.get(now-timedelta(microseconds=1), now+timedelta(microseconds=1))
    assert len(metrics) == 2
    assert metrics[CustomMetric(tag="one")][0][0] == now
    assert metrics[CustomMetric(tag="one")][0][1]["value"] == value1
    assert metrics[CustomMetric(tag="two")][0][0] == now
    assert metrics[CustomMetric(tag="two")][0][1]["value"] == value2


def test_metric_read():
    now = datetime.now(timezone.utc)
    value = uuid.uuid4().__str__()
    CustomMetric(tag="one").write(now, value=value)
    CustomMetric(tag="fake").write(now, value="fake")
    metrics = CustomMetric(tag="one").read(now-timedelta(microseconds=1), now+timedelta(microseconds=1))
    assert len(metrics) == 1
    metric = metrics[0]
    assert metric[0] == now
    assert metric[1]["value"] == value


def test_metric_read_first():
    now = datetime.now(timezone.utc)
    value = uuid.uuid4().__str__()
    CustomMetric(tag="one").write(now, value=value)
    CustomMetric(tag="one").write(now+timedelta(microseconds=1), value="fake")
    metrics = CustomMetric(tag="one").read(now-timedelta(microseconds=2), now+timedelta(microseconds=2), first=True)
    assert len(metrics) == 1
    metric = metrics[0]
    assert metric[0] == now
    assert metric[1]["value"] == value


def test_metric_read_last():
    now = datetime.now(timezone.utc)
    value = uuid.uuid4().__str__()
    CustomMetric(tag="one").write(now, value=value)
    CustomMetric(tag="one").write(now+timedelta(microseconds=-1), value="fake")
    metrics = CustomMetric(tag="one").read(now-timedelta(microseconds=2), now+timedelta(microseconds=2), last=True)
    assert len(metrics) == 1
    metric = metrics[0]
    assert metric[0] == now
    assert metric[1]["value"] == value


def test_event_write():
    now = datetime.utcnow()
    CustomEvent(tag="one", timestamp=now, value={"value": "one"}).update(value="one")


def test_events_get():
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    value1 = uuid.uuid4().__str__()
    value2 = uuid.uuid4().__str__()
    CustomEvent(tag="one", timestamp=now, value={"value": value1}).update(value=value1)
    CustomEvent(tag="two", timestamp=now, value={"value": value2}).update(value=value2)
    metrics = CustomEvent.get(now-timedelta(microseconds=1), now+timedelta(microseconds=1))
    assert len(metrics) == 2
    assert metrics[0].timestamp == now
    assert metrics[1].timestamp == now
#
#
# def test_event_read():
#     now = datetime.utcnow().replace(tzinfo=timezone.utc)
#     value = uuid.uuid4().__str__()
#     CustomEvent(tag="one", timestamp=now).write(value=value)
#     CustomEvent(tag="fake", timestamp=now).write(value="fake")
#     metrics = CustomEvent(tag="one", timestamp=now).read(now-timedelta(microseconds=1), now+timedelta(microseconds=1))
#     assert len(metrics) == 1
#     metric = metrics[0]
#     assert metric[0] == now.replace(tzinfo=timezone.utc)
#     assert metric[1]["value"] == value
