from __future__ import annotations

import json
import warnings
import zlib
from typing import Any, Protocol, runtime_checkable

# noinspection PyProtectedMember
from confluent_kafka.serialization import Deserializer
from rdflib import Dataset
from rdflib.graph import DATASET_DEFAULT_GRAPH_ID

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
class DeserializerFunction(Protocol):
    """
    A protocol for deserializer functions that can decode the raw bytes that records are stored as in underlying storage
    into some more useful Python object
    """

    def __call__(self, data: bytes | None) -> Any:
        """
        Decodes bytes into any Python object

        :param data:
            Bytes, may be None if there is nothing to deserialize and implementations must expect this possibility
        :return: Python object
        """
        raise NotImplementedError


class Deserializers:
    """
    Provides some built-in deserializer functions
    """

    @staticmethod
    def unzip_to_string(data: bytes | None) -> str | None:
        """
        A deserializer which decompresses the data with zlib and decodes into a string assuming UTF-8 encoding

        :param data: The data to decode
        :return: Decoded data
        :rtype: str
        """
        if data is None:
            return None
        return zlib.decompress(data).decode('utf-8')

    @staticmethod
    def binary_to_string(data: bytes | None) -> str | None:
        """
        A deserializer which decodes the data into a string assuming UTF-8 encoding

        :param data: The data to decode
        :return: Decoded data
        :rtype: str
        """
        if data is None:
            return None
        return data.decode('utf-8')

    @staticmethod
    def from_json(data: bytes | None) -> Any | None:
        """
        A deserializer which decodes the data into an object by deserializing it as JSON

        :param data: The data to decode which is assumed to be a UTF-8 bytes encoding of a JSON string
        :return: Python object resulting from deserializing the JSON
        """
        if data is None:
            return None
        return json.loads(data.decode('utf-8'))


class RdfDeserializer(Deserializer):
    """
    A kafka-python deserializer for RDF datasets
    """

    def __init__(self, rdf_format="nquads"):
        """
        Creates a new deserializer

        :param rdf_format:
            The default RDF format to assume when deserializing.  If not specified we're using NQuads as the default
        """
        warnings.warn(
            "`telicent_lib.sources.deserializer.RdfDeserializer` has been deprecated. "
            "You should deserialize RDF data yourself.",
            DeprecationWarning,
            stacklevel=2
        )
        self.rdf_format = rdf_format

    def __call__(self, value, ctx=None):
        """
        Deserializes a byte sequence into an RDF Dataset

        :param topic: Topic
        :param bytes_: Byte sequence to deserialize
        :return: RDF Dataset
        """
        if value is None:
            return None

        # Default to our configured default format
        actual_format = self.rdf_format

        # See Issue #23 - kafka-python doesn't currently provide access to headers at deserialization time
        # This needs us to get upstream improvements accepted there before we can support the following logic
        # Currently this isn't a blocker because all deployments will have events flowing through the system in the same
        # RDF serialization but longer term as we have deployed customer deployments and migrate to Binary RDF/RDF
        # Deltas so topics contain messages in multiple formats this will become an issue
        # if headers is not None:
        #    for key, value in headers:
        #        if key == "Content-Type":
        #            actual_format = value.decode("utf-8")
        #            break

        # Parses into a dataset, so that we can support separate data and label graphs

        # Due to RDFLib Issue #1804 we have to explicitly set the publicID to be the default Graph ID as otherwise
        # when we parse in data that doesn't have an explicit graph set, i.e. is intended for the default graph, then
        # the default RDFLib behaviour puts that into a blank node named graph.  Specifying their internal Default Graph
        # ID explicitly ensures the triples go to the default graph as intended.
        # https://github.com/RDFLib/rdflib/issues/1804
        g = Dataset()
        g.parse(data=value, format=actual_format, publicID=DATASET_DEFAULT_GRAPH_ID)
        return g
