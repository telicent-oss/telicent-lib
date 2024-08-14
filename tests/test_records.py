from __future__ import annotations

import json
import unittest
from collections.abc import Callable, Iterable
from typing import Any

from telicent_lib import Record, RecordUtils


class RecordVerifier(unittest.TestCase):

    def __validate_record__(self, record: Record, headers: Any = None, key: Any = None, value: Any = None,
                            raw: Any = None) -> None:

        self.assertIsNotNone(record)
        self.assertEqual(record.headers, headers, "Record headers don't match")
        self.assertEqual(record.key, key, "Record keys don't match")
        self.assertEqual(record.value, value, "Record values don't match")
        self.assertEqual(record.raw, raw, "Raw Records don't match")

    @staticmethod
    def __generate_records__(total: int, value_function: Callable[[int], Any] = str) -> list[Record]:
        records = []
        for i in range(1, total + 1):
            records.append(Record(None, i, value_function(i)))
        return records


class TestRecords(RecordVerifier):

    def test_empty_record_01(self) -> None:
        self.__validate_record__(Record(None, None, None, None))

    def test_empty_record_02(self) -> None:
        # Raw record should be filled by default None
        self.__validate_record__(Record(None, None, None))

    def test_record_01(self) -> None:
        # Raw record filled by default value None
        self.__validate_record__(Record(None, 1, "test"), key=1, value="test")

    def test_record_02(self) -> None:
        # Keyword parameters used to specify parameters out of default order
        self.__validate_record__(Record(value="test", headers=None, key=1), key=1, value="test")

    def test_record_03(self) -> None:
        raw = [(1, 'test')]
        self.__validate_record__(Record(None, 1, "test", raw), key=1, value="test", raw=raw)

    def test_record_headers_01(self) -> None:
        headers = [("Content-Type", b"application/turtle"), ("Exec-Path", b"foo, bar")]
        self.__validate_record__(Record(headers, 1, "test"), key=1, value="test", headers=headers)

    def test_record_headers_02(self) -> None:
        headers = [("Content-Type", b"application/turtle"), ("Exec-Path", b"foo, bar")]
        other_headers = [("Content-Type", b"application/rdf+xml")]
        self.assertNotEqual(headers, other_headers)

    def test_bad_record_01(self) -> None:
        with self.assertRaisesRegex(TypeError, expected_regex=".*missing.*required positional arguments.*"):
            Record()  # type: ignore

    def test_bad_record_02(self) -> None:
        with self.assertRaisesRegex(TypeError, expected_regex=".*missing.*required positional arguments.*"):
            Record(None)  # type: ignore

    def test_bad_record_03(self) -> None:
        with self.assertRaisesRegex(TypeError, expected_regex=".*missing.*required positional argument.*"):
            Record(None, None)  # type: ignore

    def test_bad_record_04(self) -> None:
        with self.assertRaisesRegex(TypeError, expected_regex=".*missing.*required positional arguments.*"):
            Record(raw=[(1, "test")])  # type: ignore

    def __validate_expected_headers__(self, iterable: Iterable[str | None], expected_items: list[str | None]):
        count = 0
        for i, item in enumerate(iterable):
            if i + 1 > len(expected_items):
                self.fail("More header values found than expected")
            self.assertEqual(item, expected_items[i], "Header value not as expected")
            count += 1

        self.assertEqual(count, len(expected_items), "Did not obtain expected number of headers")

    def test_encode_header_value(self):
        # Usually, we should not do that and test the methods which implement it.
        encode_header_value = RecordUtils._RecordUtils__encode_header_value

        self.assertIsNone(encode_header_value(None))

        byte_value = b'test_bytes'
        self.assertEqual(encode_header_value(byte_value), byte_value)

        str_value = 'test_string'
        self.assertEqual(encode_header_value(str_value), str_value.encode('utf-8'))

        dict_value = {'key': 'value'}
        expected_json = json.dumps(dict_value).encode('utf-8')
        self.assertEqual(encode_header_value(dict_value), expected_json)

    def test_header_access_01(self) -> None:
        # Python type annotation mean static type check will fail when we try and pass None
        # But in practise Python allows passing whatever we feel like so want to cover with tests
        self.assertIsNone(RecordUtils.get_first_header(None, "test"))  # type: ignore
        self.assertIsNone(RecordUtils.get_first_header(Record(None, "key", "value"), "test"))
        self.__validate_expected_headers__(RecordUtils.get_headers(None, "test"), [])  # type: ignore
        self.__validate_expected_headers__(RecordUtils.get_headers(Record(None, "key", "value"), "test"), [])

    def __validate_header_access__(self, headers) -> None:
        record = Record(headers, "key", "value")

        self.assertEqual(RecordUtils.get_first_header(record, "Content-Type"), "application/turtle")
        self.assertEqual(RecordUtils.get_first_header(record, "content-type"), "application/turtle")
        self.assertIsNone(RecordUtils.get_first_header(record, "No-Such-Header"))
        self.assertEqual(RecordUtils.get_first_header(record, "Exec-Path"), "foo")
        self.assertEqual(RecordUtils.get_first_header(record, "exec-path"), "foo")

        self.assertEqual(RecordUtils.get_last_header(record, "Exec-Path"), "bar")
        self.assertEqual(RecordUtils.get_last_header(record, "exec-PATH"), "bar")
        self.assertIsNone(RecordUtils.get_last_header(record, "No-Such-Header"))

        self.__validate_expected_headers__(RecordUtils.get_headers(record, "Content-Type"), ["application/turtle"])
        self.__validate_expected_headers__(RecordUtils.get_headers(record, "content-type"), ["application/turtle"])
        self.__validate_expected_headers__(RecordUtils.get_headers(record, "Content-type"), ["application/turtle"])
        self.__validate_expected_headers__(RecordUtils.get_headers(record, "Exec-Path"), ["foo", "bar"])
        self.__validate_expected_headers__(RecordUtils.get_headers(record, "exec-path"), ["foo", "bar"])
        self.__validate_expected_headers__(RecordUtils.get_headers(record, "No-Such-Header"), [])

    def test_header_access_02(self) -> None:
        headers = [("Content-Type", b"application/turtle"), ("Exec-Path", b"foo"),
                   ("Exec-Path", b"bar")]
        self.__validate_header_access__(headers)

    def test_header_access_03(self) -> None:
        # Mix of encoded and unencoded values
        headers = [("Content-Type", "application/turtle"), ("Exec-Path", b"foo"),
                   ("Exec-Path", "bar")]
        self.__validate_header_access__(headers)

    def test_header_mutation_01(self) -> None:
        record = Record(None, "key", "value")
        self.assertIsNone(record.headers)

        record2 = RecordUtils.add_header(record, "Test", "12345")
        self.assertIsNotNone(record2.headers)
        self.assertEqual(RecordUtils.get_first_header(record2, "Test"), "12345")

        record3 = RecordUtils.add_header(record2, "Test", "6789")
        self.assertIsNotNone(record3.headers)
        self.__validate_expected_headers__(RecordUtils.get_headers(record3, "Test"), ["12345", "6789"])
        self.assertEqual(RecordUtils.get_last_header(record3, "Test"), "6789")
        # Should not have mutated the original record
        self.__validate_expected_headers__(RecordUtils.get_headers(record2, "Test"), ["12345"])

    def test_header_mutation_02(self) -> None:
        headers = [("Test", b"12345"), ("test", "6789"), ("Other-Header", "foo")]
        record = Record(headers, "key", "value")
        self.assertEqual(RecordUtils.get_first_header(record, "Test"), "12345")
        self.assertEqual(RecordUtils.get_last_header(record, "Test"), "6789")
        self.__validate_expected_headers__(RecordUtils.get_headers(record, "Test"), ["12345", "6789"])
        self.assertEqual(RecordUtils.get_first_header(record, "Other-Header"), "foo")

        # Value to be removed must match an actual value
        record2 = RecordUtils.remove_header(record, "Test", "bar")
        self.assertEqual(RecordUtils.get_first_header(record2, "Test"), "12345")
        self.assertEqual(RecordUtils.get_last_header(record2, "Test"), "6789")
        self.__validate_expected_headers__(RecordUtils.get_headers(record2, "Test"), ["12345", "6789"])
        self.assertEqual(RecordUtils.get_first_header(record, "Other-Header"), "foo")

        # Value must match exactly
        record3 = RecordUtils.remove_header(record, "Test", "12345")
        self.assertEqual(RecordUtils.get_first_header(record3, "Test"), "12345")
        self.assertEqual(RecordUtils.get_last_header(record3, "Test"), "6789")
        self.__validate_expected_headers__(RecordUtils.get_headers(record3, "Test"), ["12345", "6789"])
        self.assertEqual(RecordUtils.get_first_header(record, "Other-Header"), "foo")

        # Value does match exactly
        record4 = RecordUtils.remove_header(record, "Test", b"12345")
        self.assertEqual(RecordUtils.get_first_header(record4, "Test"), "6789")
        self.assertEqual(RecordUtils.get_last_header(record4, "Test"), "6789")
        self.__validate_expected_headers__(RecordUtils.get_headers(record4, "Test"), ["6789"])
        self.assertEqual(RecordUtils.get_first_header(record, "Other-Header"), "foo")

        # Value does match exactly
        record4b = RecordUtils.remove_header(record, "Test", "6789")
        self.assertEqual(RecordUtils.get_first_header(record4b, "Test"), "12345")
        self.assertEqual(RecordUtils.get_last_header(record4b, "Test"), "12345")
        self.__validate_expected_headers__(RecordUtils.get_headers(record4b, "Test"), ["12345"])
        self.assertEqual(RecordUtils.get_first_header(record, "Other-Header"), "foo")

        # A Value of None deletes all headers with the key
        record5 = RecordUtils.remove_header(record, "Test")
        self.assertIsNone(RecordUtils.get_first_header(record5, "Test"))
        self.assertIsNone(RecordUtils.get_last_header(record5, "Test"))
        self.__validate_expected_headers__(RecordUtils.get_headers(record5, "Test"), [])
        self.assertEqual(RecordUtils.get_first_header(record, "Other-Header"), "foo")

        # Non-matching header key removes nothing
        record6 = RecordUtils.remove_header(record, "No-Such-Header")
        self.assertEqual(RecordUtils.get_first_header(record6, "Test"), "12345")
        self.assertEqual(RecordUtils.get_last_header(record6, "Test"), "6789")
        self.__validate_expected_headers__(RecordUtils.get_headers(record6, "Test"), ["12345", "6789"])
        self.assertEqual(RecordUtils.get_first_header(record6, "Other-Header"), "foo")

    def test_header_mutation_03(self) -> None:
        record = Record(None, "key", "value")
        self.assertIsNone(record.headers)

        record2 = RecordUtils.add_headers(record, [("Test", "12345"), ("Test", "6789"), ("Exec-Path", "foo"),
                                                   ("Exec-Path", "bar")])
        self.assertIsNone(record.headers)
        self.assertIsNotNone(record2.headers)
        self.assertEqual(RecordUtils.get_first_header(record2, "Test"), "12345")
        self.assertEqual(RecordUtils.get_last_header(record2, "Test"), "6789")
        self.__validate_expected_headers__(RecordUtils.get_headers(record2, "Test"), ["12345", "6789"])
        self.__validate_expected_headers__(RecordUtils.get_headers(record2, "Exec-Path"), ["foo", "bar"])

    def test_header_preparation_01(self) -> None:
        headers = RecordUtils.to_headers({"Test": "12345", "Exec-Path": "foo"})
        record = Record(headers, "key", "value")

        self.assertIsNotNone(record.headers)
        self.assertEqual(RecordUtils.get_first_header(record, "Test"), "12345")
        self.assertEqual(RecordUtils.get_last_header(record, "Test"), "12345")
        self.__validate_expected_headers__(RecordUtils.get_headers(record, "Test"), ["12345"])
        self.assertEqual(RecordUtils.get_first_header(record, "Exec-Path"), "foo")
        self.__validate_expected_headers__(RecordUtils.get_headers(record, "Exec-Path"), ["foo"])

    def test_header_preparation_02(self) -> None:
        headers: list[tuple[str, str | bytes | None]] | None = [("Test", "12345"),
                                                                        ("Exec-Path", b"foo")]
        record = Record(RecordUtils.to_headers({"Test": "6789", "Exec-Path": "bar"}, headers), "key", "value")

        self.assertIsNotNone(record.headers)
        self.assertEqual(RecordUtils.get_first_header(record, "Test"), "12345")
        self.assertEqual(RecordUtils.get_last_header(record, "Test"), "6789")
        self.__validate_expected_headers__(RecordUtils.get_headers(record, "Test"), ["12345", "6789"])
        self.assertEqual(RecordUtils.get_first_header(record, "Exec-Path"), "foo")
        self.__validate_expected_headers__(RecordUtils.get_headers(record, "Exec-Path"), ["foo", "bar"])


if __name__ == '__main__':
    unittest.main()
