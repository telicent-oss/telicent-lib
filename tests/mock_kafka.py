from __future__ import annotations

from collections.abc import Iterable
from unittest import mock

from telicent_lib import Record


class MockProducer(mock.MagicMock):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.produced_messages = {}

    def close(self, *args, **kwargs):
        pass

    def produce(self, topic, key, value, headers):
        if topic not in self.produced_messages:
            self.produced_messages[topic] = [[key, value, headers]]
        else:
            self.produced_messages[topic].append([key, value, headers])

    def flush(self, *args, **kwargs):
        pass

    def poll(self, *args, **kwargs):
        pass


class MockRecord(mock.MagicMock):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def error(self):
        return None

    def topic(self):
        return 'topic'

    def partition(self):
        return 1

    def headers(self):
        return (('my-header', 'my-header-value'),)


class MockConsumer(mock.MagicMock):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.returned_count = 0
        self.desired_message_count = 1

    def list_topics(self, *args, **kwargs):
        pass

    def subscribe(self, *args, **kwargs):
        pass

    def close(self, *args, **kwargs):
        pass

    def poll(self, *args, **kwargs):
        if self.returned_count < self.desired_message_count:
            self.returned_count += 1
            return MockRecord()
        else:
            raise StopIteration

    def commit(self, *args, **kwargs):
        pass


def fake_map_func(record: Record) -> Record | list[Record] | None:
    return record


def fake_adapter_func() -> Iterable[Record]:
    yield MockRecord()


def fake_project_func(record: Record):
    pass
