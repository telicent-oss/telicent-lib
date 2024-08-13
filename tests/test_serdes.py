from __future__ import annotations

import inspect
import unittest
from collections.abc import Callable
from json import JSONDecodeError
from typing import Any

from confluent_kafka import KafkaException
from confluent_kafka.serialization import Deserializer, Serializer
from rdflib import RDF, RDFS, BNode, Dataset, Graph, URIRef
from rdflib.compare import to_isomorphic
from rdflib.graph import DATASET_DEFAULT_GRAPH_ID

from telicent_lib.sinks import KafkaSink, Serializers
from telicent_lib.sinks.serializers import RdfSerializer, SerializerFunction
from telicent_lib.sources import Deserializers, KafkaSource
from telicent_lib.sources.deserializers import DeserializerFunction, RdfDeserializer


def __default_serdes__() -> list[tuple[Callable[[Any], bytes | None], Callable[[bytes | None], bytes | Any]]]:
    return [
        (Serializers.to_binary, Deserializers.binary_to_string),
        (Serializers.to_zipped_binary, Deserializers.unzip_to_string),
        (Serializers.to_json, Deserializers.from_json)
    ]


def __compare_rdf_graphs__(a: Any, b: Any) -> bool:
    if isinstance(a, Dataset) and isinstance(b, Dataset):
        # If we're comparing two datasets compare each graph within them
        for a_ctx in a.contexts():
            b_ctx = b.get_context(identifier=a_ctx.identifier)
            if not __compare_rdf_graphs__(a_ctx, b_ctx):
                return False
        for b_ctx in b.contexts():
            a_ctx = a.get_context(identifier=b_ctx.identifier)
            if not __compare_rdf_graphs__(a_ctx, b_ctx):
                return False
        return True

    if not isinstance(a, Dataset):
        a_iso = to_isomorphic(a)
    else:
        a_iso = to_isomorphic(a.get_context(identifier=DATASET_DEFAULT_GRAPH_ID))  # next(a.contexts()))
    if not isinstance(b, Dataset):
        b_iso = to_isomorphic(b)
    else:
        b_iso = to_isomorphic(b.get_context(identifier=DATASET_DEFAULT_GRAPH_ID))  # next(b.contexts()))

    # For debugging if tests aren't producing the expected results
    if False:
        print("A:")
        print(a_iso.serialize(destination=None, encoding=None, format="nt11"))
        print()
        print("B:")
        if isinstance(b, Dataset):
            print("Full Dataset:")
            print(b.serialize(destination=None, encoding=None, format="nquads"))
            for _, ctx in enumerate(b.contexts()):
                print(ctx.identifier)
        print(b_iso.serialize(destination=None, encoding=None, format="nt11"))

    return a_iso == b_iso


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

    def test_graph_none(self):
        serializer = RdfSerializer()
        self.assertIsNone(serializer(None))
        deserializer = RdfDeserializer()
        self.assertIsNone(deserializer(None))

    def test_graph_empty(self):
        g = Graph()
        self._verify_round_trip(g, serializer_class=RdfSerializer(), deserializer_class=RdfDeserializer(),
                                comparison_function=__compare_rdf_graphs__)

    def test_graph_simple(self):
        g = Graph()
        g.add((BNode(), RDF.type, RDFS.Class))
        self._verify_round_trip(g, serializer_class=RdfSerializer(), deserializer_class=RdfDeserializer(),
                                comparison_function=__compare_rdf_graphs__)

    def test_graph_alternate_format(self):
        g = Graph()
        g.add((BNode(), RDF.type, RDFS.Class))
        self._verify_round_trip(g, serializer_class=RdfSerializer("trig", True, "ttl"),
                                deserializer_class=RdfDeserializer("trig"),
                                comparison_function=__compare_rdf_graphs__)

    def test_dataset_empty(self):
        g = Dataset()
        self._verify_round_trip(g, serializer_class=RdfSerializer(), deserializer_class=RdfDeserializer(),
                                comparison_function=__compare_rdf_graphs__)

    def test_dataset_simple(self):
        g = Dataset()
        g.add((BNode(), RDF.type, RDFS.Class))
        self._verify_round_trip(g, serializer_class=RdfSerializer(), deserializer_class=RdfDeserializer(),
                                comparison_function=__compare_rdf_graphs__)

    def test_dataset_multiple_graphs_01(self):
        g = Dataset()
        g.add((BNode(), RDF.type, RDFS.Class))
        g.add((URIRef("https://example.org/test"), RDF.type, RDFS.Class, URIRef("https://graph")))
        self._verify_round_trip(g, serializer_class=RdfSerializer(), deserializer_class=RdfDeserializer(),
                                comparison_function=__compare_rdf_graphs__)

    def test_dataset_multiple_graphs_02(self):
        g = Dataset()
        g.add((URIRef("https://example.org/first"), RDF.type, RDFS.Class))
        g.add((URIRef("https://example.org/second"), RDF.type, RDFS.Class, URIRef("https://graph")))
        g.add((URIRef("https://example.org/third"), RDF.type, RDFS.Class, DATASET_DEFAULT_GRAPH_ID))
        self._verify_round_trip(g, serializer_class=RdfSerializer(), deserializer_class=RdfDeserializer(),
                                comparison_function=__compare_rdf_graphs__)

    def test_dataset_multiple_graphs_03(self):
        g = Dataset()
        g.add((BNode(), RDF.type, RDFS.Class))
        g.add((BNode(), RDF.type, RDFS.Class, URIRef("https://graph")))
        g.add((BNode(), RDF.type, RDFS.Class, DATASET_DEFAULT_GRAPH_ID))
        self._verify_round_trip(g, serializer_class=RdfSerializer(), deserializer_class=RdfDeserializer(),
                                comparison_function=__compare_rdf_graphs__)

    def test_dataset_multiple_graphs_04(self):
        g = Dataset()
        subject = BNode()
        g.add((subject, RDF.type, RDFS.Class))
        g.add((subject, RDF.type, RDFS.Class, URIRef("https://graph")))
        g.add((subject, RDF.type, RDFS.Class, DATASET_DEFAULT_GRAPH_ID))
        self._verify_round_trip(g, serializer_class=RdfSerializer(), deserializer_class=RdfDeserializer(),
                                comparison_function=__compare_rdf_graphs__)

    def test_dataset_multiple_graphs_alternate_format(self):
        g = Dataset()
        g.add((URIRef("https://example.org/first"), RDF.type, RDFS.Class))
        g.add((URIRef("https://example.org/second"), RDF.type, RDFS.Class, URIRef("https://graph")))
        g.add((URIRef("https://example.org/third"), RDF.type, RDFS.Class, DATASET_DEFAULT_GRAPH_ID))
        self._verify_round_trip(g, serializer_class=RdfSerializer("trig", True, "ttl"),
                                deserializer_class=RdfDeserializer("trig"),
                                comparison_function=__compare_rdf_graphs__)

    def test_serdes_validation_01(self):
        for serdes in __default_serdes__():
            serializer = serdes[0]
            deserializer = serdes[1]
            with self.subTest(serializer=serializer, deserializer=deserializer):
                self.assertTrue(inspect.ismethod(serializer) or inspect.isfunction(serializer))
                self.assertTrue(inspect.ismethod(deserializer) or inspect.isfunction(deserializer))

        self.assertTrue(isinstance(RdfSerializer(), Serializer))
        self.assertTrue(isinstance(RdfDeserializer(), Deserializer))
        self.assertFalse(inspect.ismethod(RdfSerializer) and inspect.isfunction(RdfSerializer))
        self.assertFalse(inspect.ismethod(RdfDeserializer) and inspect.isfunction(RdfDeserializer))

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

    def test_serdes_validation_05(self):
        self.assertFalse(inspect.ismethod(ExtendedSerializerFunction) or inspect.isfunction(ExtendedSerializerFunction))
        self.assertTrue(isinstance(ExtendedSerializerFunction, SerializerFunction))

        with self.assertRaises(expected_exception=KafkaException):
            KafkaSource(topic="test",
                        kafka_config={'bootstrap.servers': 'localhost:12345'},
                        key_deserializer=RdfDeserializer(),
                        value_deserializer=RdfDeserializer())

    def test_serdes_validation_bad_01(self):

        # KafkaSink(topic="test", key_serializer=RdfSerializer)
        with self.assertRaisesRegex(expected_exception=TypeError,
                                    expected_regex="not a function/method/Serializer instance.*instance of this class"):
            KafkaSink(
                topic="test",
                key_serializer=RdfSerializer
            )

    def test_serdes_validation_bad_02(self):
        with self.assertRaisesRegex(expected_exception=TypeError,
                                    expected_regex="not a function/method/Serializer instance.*instance of this class"):
            KafkaSink(
                topic="test",
                value_serializer=RdfSerializer
            )

    def test_serdes_validation_bad_03(self):
        with self.assertRaisesRegex(
                expected_exception=TypeError,
                expected_regex="not a function/method/Deserializer instance.*instance of this class"
        ):
            KafkaSource(
                topic="test",
                key_deserializer=RdfDeserializer
            )

    def test_serdes_validation_bad_04(self):
        with self.assertRaisesRegex(
                expected_exception=TypeError,
                expected_regex="not a function/method/Deserializer instance.*instance of this class"
        ):
            KafkaSource(
                topic="test",
                value_deserializer=RdfDeserializer
            )


if __name__ == '__main__':
    unittest.main()
