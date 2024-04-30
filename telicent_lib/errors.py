import datetime
import importlib
import json
import sys
import traceback
from enum import Enum

import pytz

from telicent_lib.config import Configurator
from telicent_lib.records import Record, RecordUtils
from telicent_lib.sinks import KafkaSink

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


class ErrorLevel(Enum):
    INFO = 0
    WARNING = 1
    ERROR = 2


def auto_discover_error_handler():
    config = Configurator()
    error_handler = config.get("ERROR_HANDLER_CLASS", "telicent_lib.errors.KafkaErrorHandler")
    my_module, my_class = error_handler.rsplit('.', 1)
    module = importlib.import_module(my_module)
    return getattr(module, my_class)


class ErrorHandler:

    def __init__(self, component_id):
        super().__init__()
        self.component_id = component_id
        self.headers = {"Content-Type": "application/json"}

    def set_headers(self, headers: dict, merge: bool = True):
        if merge:
            self.headers.update(headers)
        else:
            self.headers = headers

    def __send_record__(self, record: Record):
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()

    def send_exception(self, exception: Exception, level: ErrorLevel = ErrorLevel.ERROR, counter: int = 0):
        exception_list = traceback.format_stack()
        exception_list = exception_list[:-2]
        exception_list.extend(traceback.format_tb(sys.exc_info()[2]))
        exception_list.extend(traceback.format_exception_only(sys.exc_info()[0], sys.exc_info()[1]))
        stack_trace = "".join(exception_list)
        stack_trace = stack_trace[:-1]

        self.__send_record__(self.__prepare_record__(
            str(exception), stack_trace, str(exception.__class__.__name__), level, counter
        ))

    def send_error(self, error: str, error_type: str = '', level=ErrorLevel.ERROR, counter=0):
        self.__send_record__(self.__prepare_record__(
            str(error), '', error_type, level, counter
        ))

    def __prepare_record__(self, error_message, stack_trace, error_type, level, counter):
        return Record(headers=RecordUtils.to_headers(self.headers), key=None, value=json.dumps({
            'id': self.component_id,
            'error_message': error_message,
            'stack_trace': stack_trace,
            'error_type': error_type,
            'timestamp': datetime.datetime.now(pytz.utc).isoformat(),
            'level': level.name,
            'counter': counter
        }), raw=None)


class KafkaErrorHandler(ErrorHandler):

    def __init__(self, component_id, kafka_config=None, topic=None):
        super().__init__(component_id)
        if topic is None:
            config = Configurator()
            topic = config.get("ERROR_HANDLER_PROVENANCE_TOPIC", "provenance.errors")
        self.kafka_sink = KafkaSink(topic, kafka_config=kafka_config)

    def __send_record__(self, record: Record):
        self.kafka_sink.send(record)

    def close(self):
        self.kafka_sink.close()


class FileBasedErrorHandler(ErrorHandler):

    def __init__(self, component_id, file_path=None):
        super().__init__(component_id)
        if file_path is None:
            config = Configurator()
            file_path = config.get("ERROR_HANDLER_FILE_PATH", 'errors.log')
        self.f = open(file_path, "a")

    def __send_record__(self, record: Record):
        self.f.write(str(record) + "\n")

    def close(self):
        self.f.close()


class PrintErrorHandler(ErrorHandler):

    def __send_record__(self, record: Record):
        print(str(record))

    def close(self):
        pass
