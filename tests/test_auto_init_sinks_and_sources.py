from __future__ import annotations

import os
from unittest import TestCase, mock

from telicent_lib import Adapter, AutomaticAdapter, Mapper, Projector
from telicent_lib.sinks import KafkaSink
from telicent_lib.sources import KafkaSource
from tests.mock_kafka import MockConsumer, MockProducer, fake_adapter_func, fake_map_func
from tests.test_error_handler import fake_projector_function


class AutoStartSinkSourceTestCase(TestCase):

    @mock.patch.dict(os.environ, {"BOOTSTRAP_SERVERS": "localhost:1234"})
    @mock.patch.dict(os.environ, {"SOURCE_TOPIC": "source"})
    @mock.patch.dict(os.environ, {"TARGET_TOPIC": "target"})
    @mock.patch('telicent_lib.sinks.kafkaSink.Producer', MockProducer)
    @mock.patch('telicent_lib.utils.AdminClient', MockConsumer)
    @mock.patch('telicent_lib.sources.kafkaSource.Consumer', MockConsumer)
    def test_mapper_inits_source_and_sink(self):
        mapper = Mapper(map_function=fake_map_func, has_reporter=False)
        self.assertIsInstance(mapper.source, KafkaSource)
        self.assertIsInstance(mapper.target, KafkaSink)
        self.assertEqual(mapper.source.topic, 'source')
        self.assertEqual(mapper.target.topic, 'target')

    @mock.patch.dict(os.environ, {"BOOTSTRAP_SERVERS": "localhost:1234"})
    @mock.patch.dict(os.environ, {"TARGET_TOPIC": "target"})
    @mock.patch('telicent_lib.sinks.kafkaSink.Producer', MockProducer)
    @mock.patch('telicent_lib.utils.AdminClient', MockConsumer)
    def test_automatic_adapter_inits_sink(self):
        mapper = AutomaticAdapter(adapter_function=fake_adapter_func, has_reporter=False)
        self.assertIsInstance(mapper.target, KafkaSink)
        self.assertEqual(mapper.target.topic, 'target')

    @mock.patch.dict(os.environ, {"BOOTSTRAP_SERVERS": "localhost:1234"})
    @mock.patch.dict(os.environ, {"TARGET_TOPIC": "target"})
    @mock.patch('telicent_lib.sinks.kafkaSink.Producer', MockProducer)
    @mock.patch('telicent_lib.utils.AdminClient', MockConsumer)
    def test_adapter_inits_sink(self):
        mapper = Adapter(has_reporter=False)
        self.assertIsInstance(mapper.target, KafkaSink)
        self.assertEqual(mapper.target.topic, 'target')

    @mock.patch.dict(os.environ, {"BOOTSTRAP_SERVERS": "localhost:1234"})
    @mock.patch.dict(os.environ, {"SOURCE_TOPIC": "source"})
    @mock.patch('telicent_lib.utils.AdminClient', MockConsumer)
    @mock.patch('telicent_lib.sources.kafkaSource.Consumer', MockConsumer)
    def test_projector_inits_sink(self):
        mapper = Projector(projector_function=fake_projector_function, target_store="FAKE_STORE", has_reporter=False)
        self.assertIsInstance(mapper.source, KafkaSource)
        self.assertEqual(mapper.source.topic, 'source')


class ExceptionsRaisedWhenNotSetTestCase(TestCase):

    @mock.patch.dict(os.environ, {"BOOTSTRAP_SERVERS": "localhost:1234"})
    @mock.patch('telicent_lib.sinks.kafkaSink.Producer', MockProducer)
    @mock.patch('telicent_lib.utils.AdminClient', MockConsumer)
    @mock.patch('telicent_lib.sources.kafkaSource.Consumer', MockConsumer)
    def test_mapper_inits_source_and_sink(self):
        self.assertRaises(SystemExit, Mapper, map_function=fake_map_func, has_reporter=False)
