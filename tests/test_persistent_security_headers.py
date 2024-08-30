from __future__ import annotations

import os
from unittest import TestCase, mock

from telicent_lib import Record, RecordUtils
from telicent_lib.mapper import Mapper
from telicent_lib.sinks.listSink import ListSink
from telicent_lib.sources.listSource import ListSource


def __map_function_no_headers__(record: Record, **map_args) -> Record | list[Record] | None:
    headers = {
        'New-Header': 'New Header'
    }
    return Record(RecordUtils.to_headers(headers), None, None, None)


def __map_function_set_new_label__(record: Record, **map_args) -> Record | list[Record] | None:
    headers = {
        'Security-Label': 'NewLabel'
    }
    return Record(RecordUtils.to_headers(headers), None, None, None)


class PersistentSecurityHeadersTestCase(TestCase):

    def test_output_record_has_same_labels_as_input_record(self):
        headers = {
            'Security-Label': 'TestLabel'
        }
        record = Record(headers=RecordUtils.to_headers(headers), key=None, value=None, raw=None)
        source = ListSource([record])
        sink = ListSink()
        mapper = Mapper(
            source=source, target=sink, map_function=__map_function_no_headers__,
            has_reporter=False, has_error_handler=False
        )
        mapper.run()
        output_record = sink.get()[0]
        output_security_label = RecordUtils.get_last_header(output_record, 'Security-Label')
        self.assertEqual(output_security_label, headers['Security-Label'])

    def test_can_override_label(self):
        headers = {
            'Security-Label': 'TestLabel'
        }
        record = Record(headers=RecordUtils.to_headers(headers), key=None, value=None, raw=None)
        source = ListSource([record])
        sink = ListSink()
        mapper = Mapper(
            source=source, target=sink, map_function=__map_function_set_new_label__,
            has_reporter=False, has_error_handler=False
        )
        mapper.run()
        output_record = sink.get()[0]
        output_security_label = list(RecordUtils.get_headers(output_record, 'Security-Label'))
        self.assertEqual(len(output_security_label), 1)
        self.assertEqual('NewLabel', output_security_label[0])

    def test_nothing_happens_with_no_label(self):
        record = Record(headers=None, key=None, value=None, raw=None)
        source = ListSource([record])
        sink = ListSink()
        mapper = Mapper(
            source=source, target=sink, map_function=__map_function_no_headers__,
            has_reporter=False, has_error_handler=False
        )
        mapper.run()
        output_record = sink.get()[0]
        self.assertFalse(RecordUtils.has_header(output_record, 'Security-Label'))

    @mock.patch.dict(os.environ, {"DISABLE_PERSISTENT_HEADERS": "1"})
    def test_persistence_can_be_disabled(self):
        headers = {
            'Security-Label': 'TestLabel'
        }
        record = Record(headers=RecordUtils.to_headers(headers), key=None, value=None, raw=None)
        source = ListSource([record])
        sink = ListSink()
        mapper = Mapper(
            source=source, target=sink, map_function=__map_function_no_headers__,
            has_reporter=False, has_error_handler=False
        )
        mapper.run()
        output_record = sink.get()[0]
        self.assertFalse(RecordUtils.has_header(output_record, 'Security-Label'))
