from __future__ import annotations

import json
import warnings
import zlib
from typing import Any, Protocol, runtime_checkable

# noinspection PyProtectedMember
from confluent_kafka.serialization import Serializer
from rdflib import Graph

__license__ = """
Copyright (c) Telicent Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


@runtime_checkable
class SerializerFunction(Protocol):
    """
    A protocol for serializer functions that can encode Python objects into bytes
    """

    def __call__(self, data: Any) -> bytes | None:
        """
        Encodes a Python object into bytes
        :param data: Python Object
        :return: Byte representation of the object
        """
        pass


class Serializers:
    """
    Provides some built-in serializer functions
    """

    @staticmethod
    def to_zipped_binary(data: Any) -> bytes | None:
        """
        Serializes data by first converting it into bytes and then compressing those bytes with zlib

        :param data: Data to encode
        :return: Compressed data
        :rtype: bytes
        """
        if data is None:
            return None
        binary_data: bytes | None
        if isinstance(data, bytes):
            binary_data = data
        else:
            binary_data = Serializers.to_binary(data)

        if binary_data is None:
            return None
        return zlib.compress(binary_data)

    @staticmethod
    def to_binary(data: Any) -> bytes | None:
        """
        Serializes data into bytes

        If the data is already bytes then it is left unchanged.

        If the data is a string then it is encoded using UTF-8 encoding.

        For any other data type the Python built-in bytes() is called on the data.

        :param data: Data to encode
        :type data: Any
        :return: Encoded data
        :rtype: bytes
        """
        if data is None:
            return None
        if isinstance(data, bytes):
            return data
        if isinstance(data, str):
            return data.encode("utf-8")
        return bytes(data)

    @staticmethod
    def as_is(data: Any) -> bytes | None:
        """
        A serializer that assumes the data is already bytes i.e. assumes the records will already have the relevant
        fields represented as bytes.

        If the data is not bytes then a TypeError is raised

        :param data: Data
        :raises TypeError: Data is not bytes
        :return: Data as-is
        :rtype: bytes
        """
        if data is None:
            return None
        if not isinstance(data, bytes):
            raise TypeError('Expected data to already be bytes')
        return data

    @staticmethod
    def to_json(data: Any) -> bytes | None:
        """
        A serializer that converts the data into a JSON string and then encodes that into UTF-8 bytes

        If the data is None then None is returned
        :param data: Data
        :return: Bytes
        :rtype: bytes
        """
        if data is None:
            return None
        return Serializers.to_binary(json.dumps(data))


class RdfSerializer(Serializer):
    """
    A kafka-python serializer for RDF Graphs and Datasets
    """

    def __init__(self, rdf_format: str = "nquads", require_context_awareness: bool = True,
                 rdf_graph_format: str = "nt11"):
        """
        Creates a new serializer
        :param rdf_format:
            The RDF format to use for serialization.  If not specified we're using NQuads as the default.
        :param require_context_awareness:
            Whether the given `rdf_format` requires a context aware value i.e. a Dataset rather than a Graph, if True
            and the value to serialize is not context aware then falls back to the `rdf_graph_format` instead.
        :param rdf_graph_format:
            Alternative RDF format to use for serialization if the provided value to serialize is not context aware i.e.
            a Dataset.  Defaults to NTriples 1.1 since that's a subset of the NQuads format used as the default for
            `rdf_format`
        """
        warnings.warn(
            "`telicent_lib.sinks.serializers.RdfSerializer` has been deprecated. "
            "You should serialize RDF data yourself before calling `send()`.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__()
        self.rdf_format = rdf_format
        self.require_context_awareness = require_context_awareness
        self.rdf_graph_format = rdf_graph_format

    def __call__(self, obj, ctx=None):
        """
        Serializes the value assuming it's a rdflib Graph (or subclass thereof, e.g., Dataset) into a byte sequence

        :param value: Value to serialize
        :return: Serialized RDF
        """
        if obj is None:
            return None

        if not isinstance(obj, Graph):
            raise TypeError(f"Cannot serialize a value of type {type(obj)}, expected a rdflib Graph/Dataset")

        # Intentionally having RDFLib produce us bytes directly, this avoids an extra unnecessary bytes -> str -> bytes
        # round tripping.
        if not obj.context_aware and self.require_context_awareness:
            return obj.serialize(format=self.rdf_graph_format, encoding="utf-8")
        else:
            return obj.serialize(format=self.rdf_format, encoding="utf-8")
