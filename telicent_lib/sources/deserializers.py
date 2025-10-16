import json
import zlib
from typing import Any, Protocol, runtime_checkable

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
