import json
from unittest import TestCase

from freezegun import freeze_time

from telicent_lib import AutomaticAdapter, Record
from telicent_lib.sinks.listSink import ListSink


def __adapter_function_no_headers__() -> Record | list[Record] | None:
    return Record(None, None, None, None)


class DataCatalogueTestCase(TestCase):

    def test_automatic_adapter_with_source_headers(self):
        sink = ListSink()
        dc_sink = ListSink()
        adapter = AutomaticAdapter(target=sink, adapter_function=__adapter_function_no_headers__, has_reporter=False,
                                   has_error_handler=False, has_data_catalogue=True, source_name='foo.csv',
                                   source_type='file', data_catalogue_sink=dc_sink, name='TestAdapter')

        with freeze_time('2000-01-01 00:00:00+00:00'):
            adapter.update_data_catalogue()
        dc_msg = dc_sink.get()[0]
        expected_message = {
            'data-source-name': 'foo.csv', 'data-source-type': 'file',
            'data-source-last-update': '2000-01-01T00:00:00+00:00', 'component-name': 'TestAdapter'
        }
        self.assertEqual(json.loads(dc_msg.value), expected_message)
