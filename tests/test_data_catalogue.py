from __future__ import annotations

import json
from datetime import datetime
from unittest import TestCase
from unittest.mock import patch

import pytz

from telicent_lib import AutomaticAdapter, Record
from telicent_lib.sinks.listSink import ListSink


def __adapter_function_no_headers__() -> Record | list[Record] | None:
    return Record(None, None, None, None)


class DataCatalogTestCase(TestCase):

    def test_dc_sink_writes_data(self):
        sink = ListSink()
        dc_sink = ListSink()
        adapter = AutomaticAdapter(target=sink, adapter_function=__adapter_function_no_headers__, has_reporter=False,
                                   has_error_handler=False, has_data_catalog=True, source_name='foo.csv',
                                   source_type='file', data_catalog_sink=dc_sink, name='TestAdapter')

        with patch('telicent_lib.adapter.datetime.datetime') as frozen_datetime:
            mock_now = datetime(2000, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)
            frozen_datetime.now.return_value = mock_now
            adapter.update_data_catalog()
        dc_msg = dc_sink.get()[0]
        expected_message = {
            'data-source-name': 'foo.csv', 'data-source-type': 'file',
            'data-source-last-update': '2000-01-01T00:00:00+00:00', 'component-name': 'TestAdapter'
        }
        self.assertEqual(json.loads(dc_msg.value), expected_message)
