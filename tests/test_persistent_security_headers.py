from __future__ import annotations

from unittest import TestCase

from telicent_lib import Record, RecordUtils
from telicent_lib.mapper import Mapper
from telicent_lib.sinks.listSink import ListSink
from telicent_lib.sources.listSource import ListSource


def __map_function_no_headers__(record: Record, **map_args) -> Record | list[Record] | None:
    headers = {
        'New-Header': 'New Header'
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
