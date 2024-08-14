from __future__ import annotations

from collections.abc import Iterable

from telicent_lib.records import Record


class DataSource:
    """Represents a source from which data can be read"""
    def __init__(self, source_name: str = None):
        if source_name is None:
            raise TypeError("DataSource must be provided a source name")
        self.__source = source_name

    def data(self) -> Iterable[Record]:
        """Provides an iterable over the data"""
        raise NotImplementedError

    def remaining(self) -> int | None:
        """
        Returns the remaining number of records

        This may be None if this is unknown.  The return value may also change over time both as records are consumed
        from the data source and if the data source is actively receiving new records.
        """
        return None

    def get_source_name(self):
        return self.__source

    def close(self) -> None:
        """Closes the data source, allowing it to release any resources it may be holding open"""
        raise NotImplementedError

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
