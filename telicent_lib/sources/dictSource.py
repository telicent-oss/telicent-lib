
from collections.abc import Iterable

from telicent_lib.records import Record
from telicent_lib.sources.dataSource import DataSource


class DictionarySource(DataSource):
    """
    A Data Source backed by a dictionary, intended for test and development purposes only
    """

    def __init__(self, data=None):
        """
        Creates a new source backed by the given dictionary
        :param data: Dictionary
        """
        super().__init__("Dictionary")
        if data is None:
            data = {}
        self.dictionary = data
        self.iterator = None

    def data(self) -> Iterable[Record]:
        return self

    def __iter__(self):
        self.iterator = self.dictionary.copy()
        return self

    def __next__(self):
        if self.iterator is None:
            raise StopIteration
        try:
            key, value = self.iterator.popitem()
            return Record(None, key, value, None)
        except KeyError:
            self.iterator = None
            raise StopIteration from None

    def close(self) -> None:
        self.iterator = None

    def __str__(self):
        return f"In-Memory Dictionary({len(self.dictionary)} items)"
