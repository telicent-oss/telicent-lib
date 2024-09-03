from __future__ import annotations

import collections
import json
import logging
from collections.abc import Iterable, Mapping
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


logger = logging.getLogger(__name__)


Record = collections.namedtuple("Record", ["headers", "key", "value", "raw"], defaults=[None])
Record.__doc__ = "A record from a data source."
Record.headers.__doc__ = "The headers (if any) of the record.  Expressed as a list of tuples of (str, bytes)"
Record.key.__doc__ = "The key of the record, may be None if no key."
Record.value.__doc__ = "The value of the record, may be None if no value."
Record.raw.__doc__ = "Provides access to the raw record type used internally by the data source, may be useful in " \
                     "some advanced use cases. "


@runtime_checkable
class RecordMapper(Protocol):
    """
    Represents a callable function that maps an input record into zero or more output records.
    """

    def __call__(self, record: Record) -> Record | list[Record] | None:
        """
        Maps an input record into zero or more output records.
        :param record: Input record
        :type record: Record
        :return: Output record(s)
        """
        pass


@runtime_checkable
class RecordProjector(Protocol):
    """
    Represents a callable function that projects an input record out to some external system or database.
    """

    def __call__(self, record: Record) -> None:
        """
        Projects an input record out into some external system or database.
        :param record: Input record
        :type record: Record
        :return: Nothing
        """
        pass


@runtime_checkable
class RecordAdapter(Protocol):
    """
    Represents a callable that is a generator function, or that can produce such a generator.
    """

    def __call__(self) -> Iterable[Record]:
        """
        Provides an iterable of records
        :return: Iterable of records
        """
        pass


class RecordUtils:
    """
    Provides static utility methods for working with Record tuples
    """

    @staticmethod
    def __decode_header_value__(value: Any) -> str | None:
        if value is None:
            return None

        if isinstance(value, str):
            return value
        elif isinstance(value, bytes):
            return value.decode("utf-8")
        else:
            raise TypeError("Header value is not a str/bytes")

    @staticmethod
    def __encode_header_value(value: str | bytes | dict | None) -> Any:
        if value is None:
            return None
        elif isinstance(value, bytes):
            return value
        elif isinstance(value, dict):
            return json.dumps(value).encode("utf-8")
        return value.encode("utf-8")

    @staticmethod
    def get_first_header(record: Record, header: str) -> str | None:
        """
        Gets the first value for a given header (if any)

        :param record: Record
        :param header:
            Header whose value you want to retrieve, this is matched with the record header keys in a case-insensitive
            manner
        :return: First header value, or None if no such header exists
        """
        if record is None:
            return None
        elif record.headers is None:
            return None
        elif header is None:
            return None
        header = header.casefold()

        for key, value in record.headers:
            if key.casefold() == header:
                return RecordUtils.__decode_header_value__(value)
        return None

    @staticmethod
    def get_last_header(record: Record, header: str) -> str | None:
        """
        Gets the last value for a given header (if any)

        :param record: Record
        :param header:
            Header whose value you want to retrieve, this is matched with record header keys in a case-insensitive
            manner
        :return: Last Header value, or None if no such header exists
        """
        try:
            return list(RecordUtils.get_headers(record, header))[-1]
        except IndexError:
            return None

    @staticmethod
    def get_headers(record: Record, header: str) -> Iterable[str | None]:
        """
        Gets all values for a given header (if any)

        :param record: Record
        :param header:
            Header whose value(s) you want to retrieve, this is matched with the record header keys in a
            case-insensitive manner
        :return: Iterable over the header values (if any)
        """
        if record is None:
            return
        elif record.headers is None:
            return
        elif header is None:
            return
        header = header.casefold()

        for key, value in record.headers:
            if key.casefold() == header:
                yield RecordUtils.__decode_header_value__(value)
        return

    @staticmethod
    def add_header(record: Record, header: str, value: str | dict | bytes | None) -> Record:
        """
        Adds a header, this produces a new copy of the Record with the new header added

        :param record: Record
        :param header: Header key to add
        :param value: Header value to add
        :return: New record with the header added
        :raises ValueError: If no record/header key is provided
        """
        if record is None:
            raise ValueError("No record provided")
        elif header is None:
            raise ValueError("No header key provided")

        new_headers = []
        if record.headers is not None:
            for key, current_value in record.headers:
                new_headers.append((key, current_value))

        new_headers.append((header, RecordUtils.__encode_header_value(value)))
        return Record(new_headers, record.key, record.value, record.raw)

    @staticmethod
    def add_headers(record: Record, headers: list[tuple[str, str | bytes | dict | None]]) -> Record:
        """
        Adds multiple headers, this produces a new copy of the Record with the new headers added

        :param record: Record
        :param headers: New headers
        :return: New record with the headers added
        """
        if record is None:
            raise ValueError("No record provided")
        elif headers is None:
            raise ValueError("No new headers provided")
        elif not isinstance(headers, list):
            raise ValueError("Not a list of headers provided")

        if len(headers) == 0:
            return record

        new_headers = []
        if record.headers is not None:
            for key, value in record.headers:
                new_headers.append((key, value))
        for key, value in headers:
            new_headers.append((key, RecordUtils.__encode_header_value(value)))
        return Record(new_headers, record.key, record.value, record.raw)

    @staticmethod
    def replace_or_add_header(record: Record, header: str, value: str | bytes | None = None) -> Record:
        """
        Replaces or adds a header to a new copy of the record.

        If the header already exists the first instance of it has its value updated.  If the header does not exist then
        it is added as a new header.
        :param record: Record
        :param header: Header key
        :param value: Value to add/replace for the header
        :return: New record with the header replaced or added
        """
        if record is None:
            raise ValueError("No record provided")
        elif header is None:
            raise ValueError("No header key provided")
        header = header.casefold()

        new_headers = []
        replaced = False
        if record.headers is not None:
            for key, current_value in record.headers:
                if not replaced and key.casefold() == header:
                    new_headers.append((key, value))
                    replaced = True
                else:
                    new_headers.append((key, current_value))
        if not replaced:
            new_headers.append((header, value))

        return Record(new_headers, record.key, record.value, record.raw)

    @staticmethod
    def remove_header(record: Record, header: str, value: str | bytes | None = None) -> Record:
        """
        Removes a header, this produces a new copy of the Record with the header removed

        :param record: Record
        :param header: Header key to remove, this is matched in a case-insensitive manner
        :param value:
            Header value to remove, if None then any header with the key is removed, if a value then only a header with
            a key and value that match the provided parameters is removed.  Values must match exactly if a value is
            given.
        :return: New record with the specified header(s) removed
        :raises ValueError: If no record/header key is provided
        """
        if record is None:
            raise ValueError("No record provided")
        elif header is None:
            raise ValueError("No header key provided")

        if record.headers is None:
            return record
        header = header.casefold()

        new_headers = []
        for key, current_value in record.headers:
            if key.casefold() != header:
                new_headers.append((key, current_value))
            elif value is not None and value != current_value:
                new_headers.append((key, current_value))

        return Record(new_headers, record.key, record.value, record.raw)

    @staticmethod
    def to_headers(headers: Mapping[str, str | bytes | None],
                   existing_headers: list[tuple[str, str | bytes | None]] = None) \
            -> list[tuple[str, str | bytes | None]]:
        """
        Convenience function to convert from a Python dictionary into the header list format that Record's use

        :param headers: Dictionary of headers
        :param existing_headers: Existing headers to append the given headers to, a copy of these will be taken
        :return: list of header tuples
        """
        if headers is None:
            if existing_headers is None:
                return []
            else:
                return existing_headers

        new_headers = []
        if existing_headers is not None:
            for key, value in existing_headers:
                new_headers.append((key, RecordUtils.__encode_header_value(value)))
        for key, value in headers.items():
            new_headers.append((key, RecordUtils.__encode_header_value(value)))
        return new_headers

    @staticmethod
    def has_header(record: Record, header: str) -> bool:
        """
        Checks if a record has a given header.

        :param record: Record
        :param header: Header key to check for, this is matched in a case-insensitive manner
        """
        if record.headers is None:
            return False

        header = header.casefold()
        for key, _ in record.headers:
            if key.casefold() == header:
                return True
        return False
