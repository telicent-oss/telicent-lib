import inspect
import unittest
from collections.abc import Callable
from json import JSONDecodeError
from typing import Any

from confluent_kafka import KafkaException
from confluent_kafka.serialization import Deserializer, Serializer

from telicent_lib.sinks import KafkaSink, Serializers
from telicent_lib.sinks.serializers import SerializerFunction
from telicent_lib.sources import Deserializers, KafkaSource
from telicent_lib.sources.deserializers import DeserializerFunction


def __default_serdes__() -> list[tuple[Callable[[Any], bytes | None], Callable[[bytes | None], bytes | Any]]]:
    return [
        (Serializers.to_binary, Deserializers.binary_to_string),
        (Serializers.to_zipped_binary, Deserializers.unzip_to_string),
        (Serializers.to_json, Deserializers.from_json)
    ]


class ExtendedSerializerFunction(SerializerFunction):

    def __call__(self, data: Any) -> bytes | None:
        if data is None:
            return None
        return bytes(data)


class ExtendedDeserializerFunction(DeserializerFunction):

    def __call__(self, data: bytes | None) -> Any:
        return data


class TestSerdes(unittest.TestCase):

    def _verify_round_trip(self, data: Any, serializer_function: Callable[[Any], bytes | None] = None,
                           serializer_class: Serializer = None,
                           deserializer_function: Callable[[bytes | None], Any | None] = None,
                           deserializer_class: Deserializer = None,
                           comparison_function: Callable[[Any, Any], bool] = None):
        if serializer_function:
            serialized_data = serializer_function(data)
        elif serializer_class:
            serialized_data = serializer_class(data)
        else:
            self.fail("Failed to declare a serializer function/class to use")

        if deserializer_function:
            deserialized_data = deserializer_function(serialized_data)
        elif deserializer_class:
            deserialized_data = deserializer_class(serialized_data)
        else:
            self.fail("Failed to declare a deserializer function/class to use")

        if comparison_function:
            self.assertTrue(comparison_function(data, deserialized_data), "Expected data to successfully round trip")
        else:
            self.assertEqual(data, deserialized_data, "Expected data to successfully round trip")

    def test_none_serdes(self):
        for serdes in __default_serdes__():
            serializer = serdes[0]
            deserializer = serdes[1]
            with self.subTest(serializer=serializer, deserializer=deserializer):
                self._verify_round_trip(None, serializer_function=serializer, deserializer_function=deserializer)

    def test_simple_string(self):
        for serdes in __default_serdes__():
            serializer = serdes[0]
            deserializer = serdes[1]
            with self.subTest(serializer=serializer, deserializer=deserializer):
                self._verify_round_trip("test", serializer_function=serializer, deserializer_function=deserializer)

    def test_json_simple_dictionary(self):
        self._verify_round_trip({'name': 'test', 'number': 3579, 'enabled': True},
                                serializer_function=Serializers.to_json, deserializer_function=Deserializers.from_json)

    def test_json_nested_dictionary(self):
        self._verify_round_trip({'name': 'test',
                                 'alternateNames': ['example', 'other'],
                                 'number': 3579,
                                 'enabled': True,
                                 'nested': {'intermediate': {'foo': 'bar'}}},
                                serializer_function=Serializers.to_json, deserializer_function=Deserializers.from_json)

    def test_json_simple_list(self):
        self._verify_round_trip(['foo', 'bar', 'test'],
                                serializer_function=Serializers.to_json, deserializer_function=Deserializers.from_json)

    def test_json_mixed_list(self):
        self._verify_round_trip(['foo', True, 1234],
                                serializer_function=Serializers.to_json, deserializer_function=Deserializers.from_json)

    def test_json_complex_list(self):
        self._verify_round_trip(['foo', {'name': 'example', 'enabled': True}, ['sub', 'list']],
                                serializer_function=Serializers.to_json, deserializer_function=Deserializers.from_json)

    def test_invalid_json_01(self):
        bad_json = "not a json string"
        with self.assertRaises(JSONDecodeError):
            Deserializers.from_json(Serializers.to_binary(bad_json))

    def test_invalid_json_02(self):
        bad_json = "{ \"enabled\": not_a_boolean }"
        with self.assertRaises(JSONDecodeError):
            Deserializers.from_json(Serializers.to_binary(bad_json))

    def test_invalid_json_03(self):
        bad_json = "{ \"value\": \"unterminated }"
        with self.assertRaises(JSONDecodeError):
            Deserializers.from_json(Serializers.to_binary(bad_json))

    def test_invalid_json_04(self):
        bad_json = "{ \"enabled\": \"missing end of object\""
        with self.assertRaises(JSONDecodeError):
            Deserializers.from_json(Serializers.to_binary(bad_json))

    def test_serdes_validation_02(self):
        self.assertFalse(inspect.ismethod(ExtendedSerializerFunction) or inspect.isfunction(ExtendedSerializerFunction))
        self.assertTrue(isinstance(ExtendedSerializerFunction, SerializerFunction))

        with self.assertRaises(expected_exception=KafkaException):
            KafkaSink(
                topic="test", kafka_config={'bootstrap.servers': 'localhost:12345'},
                key_serializer=ExtendedSerializerFunction, value_serializer=ExtendedSerializerFunction
            )

    def test_serdes_validation_03(self):
        self.assertFalse(inspect.ismethod(ExtendedSerializerFunction) or inspect.isfunction(ExtendedSerializerFunction))
        self.assertTrue(isinstance(ExtendedSerializerFunction, SerializerFunction))

        with self.assertRaises(expected_exception=KafkaException):
            KafkaSink(topic="test",
                      kafka_config={'bootstrap.servers': 'localhost:12345'},
                      key_serializer=ExtendedSerializerFunction,
                      value_serializer=ExtendedSerializerFunction)

    def test_serdes_validation_04(self):
        self.assertFalse(inspect.ismethod(ExtendedSerializerFunction) or inspect.isfunction(ExtendedSerializerFunction))
        self.assertTrue(isinstance(ExtendedSerializerFunction, SerializerFunction))

        with self.assertRaises(expected_exception=KafkaException):
            KafkaSource(topic="test",
                        kafka_config={'bootstrap.servers': 'localhost:12345'},
                        key_deserializer=ExtendedDeserializerFunction,
                        value_deserializer=ExtendedDeserializerFunction)


if __name__ == '__main__':
    unittest.main()
