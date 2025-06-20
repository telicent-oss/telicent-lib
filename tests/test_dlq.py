from __future__ import annotations

import logging
import os
from unittest import TestCase, mock

from telicent_lib.exceptions import DLQException
from telicent_lib.mapper import Mapper
from telicent_lib.projector import Projector
from telicent_lib.records import Record
from telicent_lib.sinks.kafkaSink import KafkaSink
from telicent_lib.sources import KafkaSource

logger = logging.getLogger(__name__)


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


def map_func(record: Record) -> Record | list[Record] | None:
    raise DLQException('Test Exception')


def projector_func(record: Record) -> None:
    raise DLQException('Test Exception')


class DLQTestCase(TestCase):

    @mock.patch.dict(os.environ, {"BOOTSTRAP_SERVERS": "localhost:1234"})
    @mock.patch.dict(os.environ, {"AUTO_ENABLE_DLQ": "true"})
    @mock.patch('telicent_lib.sinks.kafkaSink.Producer', MockProducer)
    @mock.patch('telicent_lib.utils.AdminClient', MockConsumer)
    @mock.patch('telicent_lib.sources.kafkaSource.Consumer', MockConsumer)
    def test_mapper_dlq(self):
        source = KafkaSource('source_test')
        target = KafkaSink('target_test')
        mapper = Mapper(source=source, target=target, map_function=map_func, has_reporter=False)
        self.assertIsInstance(mapper.dlq_target, KafkaSink)
        self.assertEqual(mapper.dlq_target.topic, 'source_test.dlq')

        mapper.run()

        # Ensure DLQ has a message
        self.assertEqual(len(mapper.dlq_target.target.produced_messages['source_test.dlq']), 1)

        # Ensure mapper's target topic didn't get a message
        self.assertNotIn('target_test', mapper.target.target.produced_messages)

        # Ensure headers are present
        dlq_message = mapper.dlq_target.target.produced_messages['source_test.dlq'][0]
        self.assertEqual(dlq_message[2][1], ('Dead-Letter-Reason', b'Test Exception'))

    @mock.patch.dict(os.environ, {"BOOTSTRAP_SERVERS": "localhost:1234"})
    @mock.patch.dict(os.environ, {"AUTO_ENABLE_DLQ": "true"})
    @mock.patch('telicent_lib.sinks.kafkaSink.Producer', MockProducer)
    @mock.patch('telicent_lib.utils.AdminClient', MockConsumer)
    @mock.patch('telicent_lib.sources.kafkaSource.Consumer', MockConsumer)
    def test_projector_dlq(self):
        source = KafkaSource('source_test')
        projector = Projector(
            source=source, target_store='Faked', projector_function=projector_func, has_reporter=False
        )
        self.assertIsInstance(projector.dlq_target, KafkaSink)
        self.assertEqual(projector.dlq_target.topic, 'source_test.dlq')

        projector.run()

        # Ensure DLQ has a message
        self.assertEqual(len(projector.dlq_target.target.produced_messages['source_test.dlq']), 1)

        # Ensure headers are present
        dlq_message = projector.dlq_target.target.produced_messages['source_test.dlq'][0]
        self.assertEqual(dlq_message[2][1], ('Dead-Letter-Reason', b'Test Exception'))
