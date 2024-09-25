from __future__ import annotations

import json
from datetime import datetime
from unittest import TestCase
from unittest.mock import patch

import pytz

# from rdflib import Graph
from telicent_lib import AutomaticAdapter, Record
from telicent_lib.datasets.datasets import SimpleDataSet
from telicent_lib.sinks.listSink import ListSink


def __adapter_function_no_headers__() -> Record | list[Record] | None:
    return Record(None, None, None, None)


class DataCatalogTestCase(TestCase):

    def test_dc_sink_writes_update(self):
        sink = ListSink()
        dc_sink = ListSink()
        dataset = SimpleDataSet(dataset_id='id', title='foo.csv', source_mime_type='file')
        adapter = AutomaticAdapter(target=sink, adapter_function=__adapter_function_no_headers__, has_reporter=False,
                                   has_error_handler=False, has_data_catalog=True, dataset=dataset,
                                   data_catalog_sink=dc_sink, name='TestAdapter')

        with patch('telicent_lib.datasets.datasets.datetime') as frozen_datetime:
            mock_now = datetime(2000, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)
            frozen_datetime.now.return_value = mock_now
            with patch('telicent_lib.adapter.uuid.uuid4') as patched_uuid:
                patched_uuid.return_value = 'my-uuid'
                adapter.update_data_catalog()
        dc_msg = dc_sink.get()[0]
        expected_headers = [
            ('Exec-Path', b'TestAdapter'),
            ('Request-Id', b'catalog:my-uuid'),
            ('Content-Type', b'application/json')
        ]
        expected_message = {
            'id': 'id',
            'last_updated_at': '2000-01-01T00:00:00+00:00'
        }
        self.assertEqual(expected_headers, dc_msg.headers)
        self.assertEqual(json.loads(dc_msg.value), expected_message)

    def test_dc_sink_writes_registration(self):
        sink = ListSink()
        dc_sink = ListSink()
        dataset = SimpleDataSet(dataset_id='id', title='foo.csv', source_mime_type='file')
        adapter = AutomaticAdapter(target=sink, adapter_function=__adapter_function_no_headers__, has_reporter=False,
                                   has_error_handler=False, has_data_catalog=True, dataset=dataset,
                                   data_catalog_sink=dc_sink, name='TestAdapter')
        registration_fields = {
            'description': "Dataset's description",
            'publication_datetime': "2000-01-01T07:00:00+00:00",
            'publisher_id': "COMPANY-Org",
            'publisher_name': "Mr Owner",
            'publisher_email': "owner@example.com",
            'owner_id': "Data Owner",
            'rights_title': "test",
            'rights_description': "test",
            'distribution_title': "Distribution Title",
            'distribution_id': "14343-232-90019"
        }
        with patch('telicent_lib.adapter.uuid.uuid4') as patched_uuid:
            patched_uuid.return_value = 'my-uuid'
            adapter.register_data_catalog(registration_fields)
        expected_message = {
            **{'id': 'id', 'source_mime_type': 'file', 'title': 'foo.csv'},
            **registration_fields
        }
        dc_msg = dc_sink.get()[0]
        expected_headers = [
            ('Exec-Path', b'TestAdapter'),
            ('Request-Id', b'catalog:my-uuid'),
            ('Content-Type', b'application/json')
        ]
        self.assertEqual(expected_headers, dc_msg.headers)
        self.assertEqual(json.loads(dc_msg.value), expected_message)
