import json
from abc import ABC, abstractmethod
from collections.abc import Mapping
from datetime import datetime

from rdflib import Graph

from telicent_lib.records import Record


class DataSetFieldError(Exception):
    pass


class DataSet(ABC):

    def __init__(self, dataset_id: str, title: str, source_mime_type: str):
        self.dataset_id = dataset_id
        self.title = title
        self.source_mime_type = source_mime_type

    @abstractmethod
    def registration_record(self, registration_fields: Mapping,
                            headers: list[str | bytes | None] = None) -> Record:
        pass

    @abstractmethod
    def update_record(self, headers: list[str | bytes | None] = None) -> Record:
        pass


class DCATDataSet(DataSet):

    def registration_record(self, registration_fields: Mapping,
                            headers: list[str | bytes | None] = None) -> Record:
        expected_fields = [
            'description', 'publication_datetime', 'published_id', 'published_name', 'publisher_email',
            'owner_id', 'rights_title', 'rights_description', 'distribution_title', 'distribution_id'
        ]
        for field in expected_fields:
            if registration_fields.get(field) is None:
                raise DataSetFieldError(f'field "{field}" is required to register dataset')
        g = Graph()
        return Record(headers, None, g.serialize(format="turtle"), None)

    def update_record(self, headers: list[str | bytes | None] = None) -> Record:
        g = Graph()
        return Record(headers, None, g.serialize(format="turtle"), None)


class SimpleDataSet(DataSet):

    def registration_record(self, registration_fields: Mapping,
                            headers: list[str | bytes | None] = None) -> Record:
        core_data = {'id': self.dataset_id, 'title': self.title, 'source_mime_type': self.source_mime_type}
        record_data = {**core_data, **registration_fields}
        return Record(headers, None, json.dumps(record_data), None)

    def update_record(self, headers: list[str | bytes | None] = None) -> Record:
        record_data = {
            'id': self.dataset_id, 'last_updated_at': datetime.now().astimezone().isoformat()
        }
        return Record(headers, None, json.dumps(record_data), None)
