from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Mapping
from datetime import datetime

from rdflib import DCAT, DCTERMS, PROV, RDF, SDO, XSD, BNode, Graph, Literal, URIRef

from telicent_lib.records import Record


class DataSetFieldError(Exception):
    pass


class DataSet(ABC):

    def __init__(self, dataset_id: str, title: str, source_mime_type: str):
        self.dataset_id = dataset_id
        self.title = title
        self.source_mime_type = source_mime_type

    @abstractmethod
    def registration_record(self, registration_fields: Mapping, headers: list[str | bytes | None] = None) -> Record:
        pass

    @abstractmethod
    def update_record(self, headers: list[str | bytes | None] = None) -> Record:
        pass

    @property
    @abstractmethod
    def content_type(self):
        pass


class DCATDataSet(DataSet):

    def __init__(self, dataset_id: str, title: str, source_mime_type: str):
        super().__init__(dataset_id, title, source_mime_type)
        self.tcat = 'http://telicent.io/catalog#'
        self.dataset_id_dataset = URIRef(f'{self.tcat}{self.dataset_id}_dataset')
        self.dataset_id_distribution = URIRef(f'{self.tcat}{self.dataset_id}_distribution')

    @property
    def content_type(self):
        return 'text/turtle'

    def registration_record(self, registration_fields: Mapping, headers: list[str | bytes | None] = None) -> Record:
        expected_fields = [
            'description', 'publication_datetime', 'publisher_id', 'publisher_name', 'publisher_email',
            'owner_id', 'rights_title', 'rights_description', 'distribution_title', 'distribution_id',
        ]
        for field in expected_fields:
            if registration_fields.get(field) is None:
                raise DataSetFieldError(f'field "{field}" is required to register dataset')
        g = Graph()
        g.bind('tcat', URIRef(self.tcat))
        g.add((self.dataset_id_dataset, RDF.type, URIRef(f'{DCAT}Dataset')))
        g.add((self.dataset_id_dataset, URIRef(f'{DCTERMS}description'), Literal(registration_fields['description'])))
        g.add((self.dataset_id_dataset, URIRef(f'{DCTERMS}title'), Literal(self.title, lang='en')))
        g.add((self.dataset_id_dataset, URIRef(f'{DCTERMS}identifier'), Literal(self.dataset_id)))
        g.add((
            self.dataset_id_dataset,
            URIRef(f'{DCTERMS}publisher'),
            URIRef(f'{self.tcat}{registration_fields["publisher_id"]}')
        ))
        g.add((
            self.dataset_id_dataset,
            URIRef(f'{DCTERMS}issued'),
            Literal(registration_fields['publication_datetime'], datatype=XSD.dateTime)
        ))

        qualified_attribution_bnode = BNode()
        g.add((self.dataset_id_dataset, URIRef(f'{PROV}qualifiedAttribution'), qualified_attribution_bnode))
        g.add((qualified_attribution_bnode, RDF.type, URIRef(f'{PROV}Attribution')))
        g.add((qualified_attribution_bnode, URIRef(f'{PROV}agent'), Literal(registration_fields['owner_id'])))
        g.add((
            qualified_attribution_bnode,
            URIRef(f'{DCAT}hadRole'),
            URIRef('http://standards.iso.org/iso/19115/resources/Codelist/cat/codelists.xml#CI_RoleCode/owner')
        ))

        rights_bnode = BNode()
        g.add((self.dataset_id_dataset, URIRef(f'{DCTERMS}rights'), rights_bnode))
        g.add((rights_bnode, URIRef(f'{DCTERMS}title'), Literal(registration_fields['rights_title'])))
        g.add((rights_bnode, URIRef(f'{DCTERMS}description'), Literal(registration_fields['rights_description'])))

        g.add((self.dataset_id_dataset, URIRef(f'{DCAT}distribution'), self.dataset_id_distribution))

        g.add((self.dataset_id_distribution, RDF.type, URIRef(f'{DCAT}Distribution')))
        g.add((
            self.dataset_id_distribution,
            URIRef(f'{DCTERMS}title'),
            Literal(registration_fields['distribution_title'], lang='en')
        ))
        g.add((
            self.dataset_id_distribution,
            URIRef(f'{DCTERMS}identifier'),
            Literal(registration_fields['distribution_id'])
        ))
        g.add((
            self.dataset_id_distribution,
            URIRef(f'{DCAT}mediaType'),
            URIRef(f'http://www.iana.org/assignments/media-types/{self.source_mime_type}')
        ))

        g.add((
            URIRef(f'{self.tcat}{registration_fields["publisher_id"]}'),
            URIRef(f'{SDO}name'),
            Literal(f'{registration_fields["publisher_name"]}', lang='en')
        ))
        g.add((
            URIRef(f'{self.tcat}{registration_fields["publisher_id"]}'),
            URIRef(f'{SDO}email'),
            URIRef(f'{registration_fields["publisher_email"]}')
        ))
        return Record(headers, None, g.serialize(format="turtle"), None)

    def update_record(self, headers: list[str | bytes | None] = None) -> Record:
        g = Graph()
        g.bind('tcat', URIRef(self.tcat))
        g.add((self.dataset_id_dataset, RDF.type, URIRef(f'{DCAT}Dataset')))
        g.add((
            self.dataset_id_dataset,
            URIRef(f'{DCTERMS}modified'),
            Literal(datetime.now().astimezone().isoformat(), datatype=XSD.dateTime)
        ))
        return Record(headers, None, g.serialize(format="turtle"), None)


class SimpleDataSet(DataSet):

    def __init__(self, dataset_id: str, title: str, source_mime_type: str):
        super().__init__(dataset_id, title, source_mime_type)

    @property
    def content_type(self):
        return 'application/json'

    def registration_record(self, registration_fields: Mapping, headers: list[str | bytes | None] = None) -> Record:
        core_data = {
            'id': self.dataset_id,
            'title': self.title,
            'source_mime_type': self.source_mime_type
        }
        record_data = {**core_data, **registration_fields}
        return Record(headers, None, json.dumps(record_data), None)

    def update_record(self, headers: list[str | bytes | None] = None) -> Record:
        record_data = {
            'id': self.dataset_id,
            'last_updated_at': datetime.now().astimezone().isoformat()
        }
        return Record(headers, None, json.dumps(record_data), None)
