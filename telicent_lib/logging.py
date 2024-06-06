from __future__ import annotations

import json
import logging
from collections.abc import MutableMapping
from typing import Any

from confluent_kafka import KafkaException

from telicent_lib import Record, RecordUtils
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


class CoreLogFormats:
    BASIC = ['name', 'levelname', 'msg', 'created']
    CORE = ['name', 'log_type', 'levelname', 'msg', 'created']


MERGE = 0
REPLACE = 1


class CoreLoggerAdapter(logging.LoggerAdapter):

    def __init__(self, logger: logging.Logger, headers: dict = None,
                 log_type: str = None, extra: dict = None, header_method: int = MERGE):
        if extra is None:
            extra = {}
        super().__init__(logger, extra)
        if headers is None:
            headers = {}
        self.headers = headers
        self.log_type = log_type
        self.header_method = header_method

    def process(self, msg: str, kwargs: MutableMapping[str, Any]) -> tuple[Any, MutableMapping[str, Any]]:
        extra = kwargs.get('extra', {})

        if 'header_method' in kwargs:
            header_method = kwargs.pop('header_method')
        else:
            header_method = self.header_method

        if 'headers' in kwargs:
            if header_method == MERGE:
                extra['headers'] = self.headers.copy()
                extra['headers'].update(kwargs.pop('headers'))
            else:
                extra['headers'] = kwargs.pop('headers')
        else:
            extra['headers'] = self.headers

        if 'log_type' in kwargs:
            extra['log_type'] = kwargs.pop('log_type')
        else:
            extra['log_type'] = self.log_type

        kwargs['extra'] = extra
        return msg, kwargs


class KafkaHandler(logging.Handler):

    def __init__(self, kafka_config: dict | None = None, topic: str = 'log', level=logging.NOTSET):
        super().__init__(level)
        try:
            self.sink = KafkaSink(topic, kafka_config=kafka_config)
        except KafkaException as e:
            raise RuntimeError('Could not initialise KafkaSink for logging. Is Kafka running?') from e

    def emit(self, record: logging.LogRecord) -> None:
        try:
            headers = record.__dict__.get('headers', {})
            msg = self.format(record)
            self.sink.send(Record(RecordUtils.to_headers(headers), None, msg, None))
            self.flush()
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)

    def close(self):
        self.sink.close()
        super().close()


class JSONFormatter(logging.Formatter):

    def __init__(self, fmt: list = None, datefmt: str = None, style='%', validate=True, *, defaults=None):
        del style, validate, defaults  # Unused
        self.datefmt = datefmt
        if fmt is None:
            self.fmt = CoreLogFormats.BASIC
        else:
            self.fmt = fmt

    def format(self, record: logging.LogRecord) -> str:
        log_dict = {}
        for fmt_kwarg in self.fmt:
            if fmt_kwarg == 'created':
                log_dict[fmt_kwarg] = self.formatTime(record)
            else:
                log_dict[fmt_kwarg] = record.__dict__[fmt_kwarg]
        return json.dumps(log_dict)


class CoreLoggerFactory:

    @staticmethod
    def get_logger(
            name: str, kafka_config: dict | None = None, topic: str = 'log', level: int = logging.INFO,
            fmt: list | None = None, headers: dict | None = None, log_type: str | None = None,
            header_method: int = MERGE
    ) -> CoreLoggerAdapter:

        logger = logging.getLogger(name)
        logger.setLevel(level)

        handler = KafkaHandler(kafka_config, topic, level)
        if fmt is None:
            fmt = CoreLogFormats.CORE

        handler.setFormatter(JSONFormatter(fmt))

        logger.addHandler(handler)
        core_logger = CoreLoggerAdapter(logger, headers=headers, log_type=log_type, header_method=header_method)

        return core_logger
