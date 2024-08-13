import unittest

from confluent_kafka import KafkaException

from telicent_lib.sources import KafkaSource


class TestSources(unittest.TestCase):

    def test_kafka_source_01(self):
        with self.assertRaises(expected_exception=KafkaException):
            KafkaSource(topic="test", kafka_config={'bootstrap.servers': 'localhost:12345'})

    def test_kafka_source_02(self):
        with self.assertRaises(expected_exception=KafkaException):
            # Multiple brokers in a single comma separated string
            KafkaSource(topic="test", kafka_config={'bootstrap.servers': 'localhost:12345,localhost:6789'})

    def test_kafka_source_03(self):
        with self.assertRaises(expected_exception=KafkaException):
            # Multiple brokers in a list
            KafkaSource(topic="test", kafka_config={'bootstrap.servers': ['localhost:12345', 'localhost:6789']})


if __name__ == '__main__':
    unittest.main()
