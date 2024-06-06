
from collections.abc import Iterable

from telicent_lib.records import Record
from telicent_lib.sources.dataSource import DataSource


class ListSource(DataSource):
    """
        A Data Source backed by a list, intended for test and development purposes only
    """

    def __init__(self, data=None):
        """
        Creates a new list source backed by the given list
        :param data: List of records
        """
        super().__init__("List")
        if data is None:
            data = []
        self.list = data
        self.index = -1

    def data(self) -> Iterable[Record]:
        return self

    def __iter__(self):
        self.index = -1
        return self

    def __next__(self):
        self.index += 1
        if self.index >= len(self.list):
            raise StopIteration
        return self.list[self.index]

    def close(self) -> None:
        self.index = -1

    def __str__(self):
        return f"In-Memory List({len(self.list)} records)"
