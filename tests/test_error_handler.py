from __future__ import annotations

import json
from collections.abc import Iterable
from unittest import TestCase, mock

from telicent_lib import AutomaticAdapter, Mapper, Projector, Record
from telicent_lib.errors import ErrorHandler, ErrorLevel
from telicent_lib.sinks.listSink import ListSink
from telicent_lib.sources.listSource import ListSource


class FakeErrorHandler(ErrorHandler):

    def __init__(self):
        super().__init__('test-id')
        self.errors = []
        self.closed = False

    def __send_record__(self, record):
        self.errors.append(record)

    def close(self):
        self.closed = True


def fake_adapter_function() -> Iterable[Record]:
    raise Exception('Test Exception')


def fake_mapper_function(record: Record) -> Record | list[Record] | None:
    raise Exception('Test Exception')


def fake_projector_function(record: Record) -> None:
    raise Exception('Test Exception')


class ErrorHandlerTestCaseStub(TestCase):

    def setUp(self) -> None:
        self.error_handler = FakeErrorHandler()

    def tearDown(self) -> None:
        del self.error_handler


class ErrorHandlerTestCase(ErrorHandlerTestCaseStub):

    def test_send_exception(self):
        try:
            raise Exception('Test Exception')
        except Exception as e:
            self.error_handler.send_exception(e)

        self.assertEqual(1, len(self.error_handler.errors))
        error_record = self.error_handler.errors[0]
        self.assertEqual(error_record.headers, [('Content-Type', b'application/json')])
        record_json = json.loads(error_record.value)
        self.assertEqual(record_json['error_message'], 'Test Exception')
        self.assertEqual(record_json['id'], 'test-id')
        self.assertEqual(record_json['error_type'], 'Exception')
        self.assertEqual(record_json['level'], ErrorLevel.ERROR.name)

    def test_send_error(self):
        self.error_handler.send_error('Test Error', 'TestType', ErrorLevel.WARNING)
        self.assertEqual(1, len(self.error_handler.errors))

        error_record = self.error_handler.errors[0]
        self.assertEqual(error_record.headers, [('Content-Type', b'application/json')])

        record_json = json.loads(error_record.value)
        self.assertEqual(record_json['error_message'], 'Test Error')
        self.assertEqual(record_json['id'], 'test-id')
        self.assertEqual(record_json['error_type'], 'TestType')
        self.assertEqual(record_json['level'], ErrorLevel.WARNING.name)


class ErrorHandlerUseCaseTestCase(ErrorHandlerTestCaseStub):

    @mock.patch('telicent_lib.errors.ErrorHandler.send_exception')
    def test_adaptor_error_handler(self, mocked_send_exception):
        adapter = AutomaticAdapter(
            adapter_function=fake_adapter_function,
            target=ListSink(), name='test-name', error_handler=self.error_handler,
            has_reporter=False, has_data_catalog=False,
        )
        try:
            adapter.run()
        except Exception:
            pass

        self.assertEqual(1, mocked_send_exception.call_count)

    @mock.patch('telicent_lib.errors.ErrorHandler.send_exception')
    def test_mapper_error_handler(self, mocked_send_exception):
        mapper = Mapper(
            map_function=fake_mapper_function, source=ListSource(['one', 'two']),
            target=ListSink(), name='test-name', error_handler=self.error_handler,
            has_reporter=False,
        )
        try:
            mapper.run()
        except Exception:
            pass

        self.assertEqual(1, mocked_send_exception.call_count)

    @mock.patch('telicent_lib.errors.ErrorHandler.send_exception')
    def test_projector_error_handler(self, mocked_send_exception):
        projector = Projector(
            projector_function=fake_projector_function, source=ListSource(['one', 'two']),
            target=ListSink(), name='test-name', error_handler=self.error_handler,
            has_reporter=False, target_store='Test'
        )
        try:
            projector.run()
        except Exception:
            pass

        self.assertEqual(1, mocked_send_exception.call_count)
