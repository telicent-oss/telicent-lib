

from telicent_lib.records import Record
from telicent_lib.sinks import DataSink

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


class ListSink(DataSink):
    """
    A Data Sink backed by a List intended for test and development purposes only
    """

    def __init__(self):
        super().__init__("List")
        self.data: list[Record] = []

    def send(self, record: Record):
        if record is None:
            return
        self.data.append(record)

    def get(self) -> list[Record]:
        """Gets the underlying list"""
        return self.data

    def __str__(self):
        return "In-Memory List"
