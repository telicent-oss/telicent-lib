import json
import unittest
from datetime import datetime, timezone
from typing import Iterable
from unittest.mock import patch

from telicent_lib import Adapter, AutomaticAdapter, Record
from telicent_lib.sinks.listSink import ListSink
from tests.delaySink import DelaySink
from tests.test_records import RecordVerifier


def datetime_encoder(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")

def integer_generator() -> Iterable[Record]:
    for i in range(0, 10):
        yield Record(headers=None, key=i, value=str(i))


def custom_range_generator(**range_args) -> Iterable[Record]:
    for i in range(range_args["start"], range_args["stop"]):
        yield Record(headers=None, key=i, value=str(i))

    if "raise_error" in range_args.keys():
        raise ValueError(range_args["raise_error"])


def error_generator() -> Iterable[Record]:
    raise RuntimeError("Failed")


class TestAdapter(RecordVerifier):

    def setUp(self) -> None:
        super().setUp()
        self.default_headers = [
            ('Exec-Path', b'Automatic Adapter-to-In-Memory List'), ('Request-Id', b'List:uuid4'), ('traceparent', b'')
        ]

        self.test_policy = {
            "apiVersion": "v1alpha",
            "specification": "UKIC v3.0",
            "identifier": "ItemA",
            "classification": "S",
            "permittedOrgs": [
                "ABC",
                "DEF",
                "HIJ"
            ],
            "permittedNats": [
                "GBR",
                "FRA",
                "IRL"
            ],
            "orGroups": [
                "Apple",
                "SOMETHING"
            ],
            "andGroups": [
                "doctor",
                "admin"
            ],
            "createdDateTime": datetime(2023, 2, 2, 23, 11, 11, 4892).astimezone(timezone.utc),
            "originator": "TestOriginator",
            "custodian": "TestCustodian",
            "policyRef": "TestPolicyRef",
            "dataSet": ["ds1", "ds2"],
            "authRef": ["ref1", "ref2"],
            "dispositionDate": datetime(2023,1,1,23,11,11).astimezone(timezone.utc),
            "dispositionProcess": "disp-process-1",
            "dissemination": ["news", "articles"]
        }

        self.bytes_policy = json.dumps({'EDH': self.test_policy}, default=datetime_encoder).encode('utf-8')
        self.default_headers_edh = [('Exec-Path', b'Automatic Adapter-to-In-Memory List'),
                                    ('Request-Id', b'List:uuid4'), ('traceparent', b''),
                                    ('policyInformation', self.bytes_policy),
                                    ('Security-Label', b'(classification=S&(permitted_organisations=ABC|'
                                                       b'permitted_organisations=DEF|permitted_organisations=HIJ)&'
                                                       b'(permitted_nationalities=GBR|permitted_nationalities=FRA|'
                                                       b'permitted_nationalities=IRL)&doctor:and&admin:and&(Apple:or|'
                                                       b'SOMETHING:or))')]

    def __validate_generated_range__(self, sink: ListSink, start: int = 0, stop: int = 10, headers=None):
        self.assertEqual(len(sink.get()), stop - start)

        for i in range(0, stop - start):
            actual = sink.get()[i]
            expected_key = start + i
            expected_value = str(expected_key)
            self.__validate_record__(record=actual, headers=headers, key=expected_key, value=expected_value)

    def test_bad_adapter_01(self):
        with self.assertRaisesRegex(ValueError, expected_regex=".* cannot be None"):
            AutomaticAdapter(target=None, adapter_function=integer_generator, has_reporter=False,
                             has_error_handler=False)

    def test_bad_adapter_02(self):
        with self.assertRaisesRegex(TypeError, expected_regex=".*Data Sink as required"):
            AutomaticAdapter(target=TestAdapter, adapter_function=integer_generator, has_reporter=False,
                             has_error_handler=False)

    def test_adapter_01(self):
        sink = ListSink()
        adapter = Adapter(target=sink, has_reporter=False, has_error_handler=False)
        adapter.run()
        for i in range(0, 10):
            adapter.send(Record(None, i, str(i)))
        adapter.finished()

        self.__validate_generated_range__(sink)

    def test_adapter_02(self):
        sink = ListSink()
        adapter = Adapter(target=sink, has_reporter=False, has_error_handler=False)
        adapter.run()
        for _ in range(0, 10):
            adapter.send(None)
        adapter.finished()

        self.assertEqual(len(sink.get()), 0)

    def test_adapter_03(self):
        sink = DelaySink()
        adapter = Adapter(target=sink, has_reporter=False, has_error_handler=False)
        adapter.run()
        for i in range(0, 10):
            adapter.send(Record(None, i, str(i)))
        adapter.finished()

        self.__validate_generated_range__(sink)

    def test_adapter_04(self):
        sink = DelaySink()
        adapter = Adapter(target=sink, has_reporter=False, has_error_handler=False)
        adapter.run()
        for i in range(0, 10):
            adapter.send(Record(None, i, str(i)))
        adapter.aborted()

        self.__validate_generated_range__(sink)

    def test_bad_automatic_adapter_01(self):
        with self.assertRaisesRegex(TypeError, expected_regex=".*required positional argument.*adapter_function.*"):
            AutomaticAdapter(target=ListSink(), has_reporter=False, has_error_handler=False)

    def test_bad_automatic_adapter_02(self):
        with self.assertRaisesRegex(ValueError, expected_regex=".*cannot be None"):
            AutomaticAdapter(target=ListSink(), adapter_function=None, has_reporter=False, has_error_handler=False)

    def test_bad_mapper_03(self):
        with self.assertRaisesRegex(TypeError, expected_regex=".*for protocol.*RecordAdapter.*"):
            AutomaticAdapter(target=ListSink(), adapter_function=str, has_reporter=False, has_error_handler=False)

    def test_automatic_adapter_01(self):
        sink = ListSink()
        adapter = AutomaticAdapter(target=sink, adapter_function=integer_generator, has_reporter=False,
                                   has_error_handler=False)
        adapter.run()
        self.assertEqual(len(sink.get()), 10)

    def test_automatic_adapter_02(self):
        sink = ListSink()
        adapter = AutomaticAdapter(target=sink, adapter_function=error_generator, has_reporter=False,
                                   has_error_handler=False)
        with self.assertRaisesRegex(expected_exception=RuntimeError, expected_regex="Failed"):
            adapter.run()
        self.assertEqual(len(sink.get()), 0)

    def test_automatic_adapter_03(self):
        sink = DelaySink()
        adapter = AutomaticAdapter(target=sink, adapter_function=integer_generator, has_reporter=False,
                                   has_error_handler=False)
        adapter.run()
        self.assertEqual(len(sink.get()), 10)

    @patch('telicent_lib.adapter.uuid.uuid4')
    def test_automatic_adapter_with_security_policy_01(self, patched_method):
        patched_method.return_value = 'uuid4'
        sink = ListSink()
        adapter = AutomaticAdapter(target=sink, adapter_function=custom_range_generator, has_reporter=False,
                                   has_error_handler=False, policy_information=self.test_policy,
                                   start=100, stop=200)
        adapter.run()
        self.__validate_generated_range__(sink, 100, 200, headers=self.default_headers_edh)

    @patch('telicent_lib.adapter.uuid.uuid4')
    def test_automatic_adapter_with_args_01(self, patched_method):
        patched_method.return_value = 'uuid4'
        sink = ListSink()
        adapter = AutomaticAdapter(target=sink, adapter_function=custom_range_generator, has_reporter=False,
                                   has_error_handler=False, start=100, stop=200)
        adapter.run()
        self.__validate_generated_range__(sink, 100, 200, headers=self.default_headers)

    @patch('telicent_lib.adapter.uuid.uuid4')
    def test_automatic_adapter_with_args_02(self, patched_method):
        patched_method.return_value = 'uuid4'
        sink = DelaySink()
        adapter = AutomaticAdapter(target=sink, adapter_function=custom_range_generator, has_reporter=False,
                                   has_error_handler=False, start=50, stop=70, raise_error="Bad source")
        with self.assertRaisesRegex(ValueError, expected_regex="Bad source"):
            adapter.run()
        self.__validate_generated_range__(sink, 50, 70, headers=self.default_headers)


if __name__ == '__main__':
    unittest.main()
