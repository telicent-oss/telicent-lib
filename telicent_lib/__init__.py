from telicent_lib.adapter import Adapter, AutomaticAdapter
from telicent_lib.datasets import DCATDataSet, SimpleDataSet
from telicent_lib.mapper import Mapper
from telicent_lib.projector import Projector
from telicent_lib.records import Record, RecordAdapter, RecordMapper, RecordProjector, RecordUtils

__license__ = """
Copyright (c) Telicent Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


__all__ = [
    'Adapter',
    'AutomaticAdapter',
    'DCATDataSet',
    'Mapper',
    'Projector',
    'Record',
    'RecordMapper',
    'RecordProjector',
    'RecordAdapter',
    'RecordUtils',
    'SimpleDataSet',
]
