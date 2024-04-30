from telicent_lib.records import Record

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


class DataSink:
    """Represents a sink to which data can be sent"""
    def __init__(self, target_name: str = None):
        if target_name is None:
            raise TypeError("Target name must be provided to DataSink")
        self.__sink = target_name

    def send(self, record: Record) -> None:
        """
        Sends some data to the sink

        :param record: The record to send to the sink
        :type record: Record
        """
        raise NotImplementedError

    def get_sink_name(self):
        return self.__sink

    def close(self):
        """Closes the sink allowing it to free any resources it may be holding open"""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
