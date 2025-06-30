from __future__ import annotations

import logging
import uuid
from collections.abc import Iterable, Mapping
from typing import Any

from colored import Fore
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from telicent_lib.action import DEFAULT_REPORTING_BATCH_SIZE, OutputAction
from telicent_lib.config import Configurator
from telicent_lib.datasets.datasets import SimpleDataSet
from telicent_lib.records import Record, RecordAdapter, RecordUtils
from telicent_lib.sinks import KafkaSink
from telicent_lib.sinks.dataSink import DataSink
from telicent_lib.status import Status
from telicent_lib.utils import validate_callable_protocol

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


logger = logging.getLogger(__name__)


class BaseAdapter(OutputAction):

    def __init__(self, target: DataSink | None, action, name,
                 text_colour, reporting_batch_size,
                 has_reporter, reporter_sink: DataSink, has_error_handler, error_handler,
                 disable_metrics, has_data_catalog, data_catalog_sink, dataset=None):

        config = Configurator()
        self.data_catalog_topic = config.get("DATA_CATALOG_TOPIC", "catalog")
        self.dataset = dataset
        if self.dataset is None:
            self.dataset = SimpleDataSet(dataset_id=__name__, title=__name__, source_mime_type='unknown')
        self.has_data_catalog = has_data_catalog
        self.data_catalog_sink = data_catalog_sink
        if self.has_data_catalog and self.data_catalog_sink is None:
            self.data_catalog_sink = KafkaSink(topic=self.data_catalog_topic)

        super().__init__(
            target, text_colour=text_colour, reporting_batch_size=reporting_batch_size,
            action=action, name=name, has_reporter=has_reporter, reporter_sink=reporter_sink,
            has_error_handler=has_error_handler, error_handler=error_handler, disable_metrics=disable_metrics
        )

    def finished(self) -> None:
        if self.has_data_catalog:
            self.data_catalog_sink.close()
        super().finished()

    def aborted(self) -> None:
        if self.has_data_catalog:
            self.data_catalog_sink.close()
        super().aborted()

    def update_data_catalog(self, headers: list[tuple[str, str | bytes | None]] = None) -> bool:
        if not self.has_data_catalog:
            logger.warning("Cannot create data catalogue update as 'has_data_catalogue' is False")
            return False
        record = self.dataset.update_record(headers)
        return self.send_catalog_record_to_broker(record)

    def register_data_catalog(self, registration_fields: Mapping,
                              headers: list[tuple[str, str | bytes | None]] = None) -> bool:
        if not self.has_data_catalog:
            logger.warning("Cannot create data catalogue update as 'has_data_catalogue' is False")
            return False
        record = self.dataset.registration_record(registration_fields, headers)
        return self.send_catalog_record_to_broker(record)

    def send_catalog_record_to_broker(self, record: Record):
        default_headers: list[tuple[str, str | bytes | dict[Any, Any] | None]] = [
            ('Exec-Path', self.generated_id),
            ('Request-Id', f'{self.data_catalog_topic}:{str(uuid.uuid4())}'),
            ('Content-Type', self.dataset.content_type)
        ]
        record = RecordUtils.add_headers(record, default_headers)
        self.data_catalog_sink.send(record)
        return True


class Adapter(BaseAdapter):
    """
    An adapter is an action for importing data to a Data Sink.

    This differs from a `Mapper` in that the data source is managed entirely by the caller who must read the data source
    themselves, transform the records and call the `send()` method of the adapter to send records to the data sink.
    """

    def __init__(self, target: DataSink | None = None, text_colour=Fore.light_cyan,
                 reporting_batch_size=DEFAULT_REPORTING_BATCH_SIZE,
                 name: str = None, dataset=None, has_reporter: bool = True,
                 reporter_sink=None, has_error_handler: bool = True, error_handler=None, disable_metrics: bool = False,
                 has_data_catalog: bool = True, data_catalog_sink = None):
        """
        Creates a new adapter that imports data into a data sink.

        :param target: A sink for the data
        :type target: DataSink
        :param text_colour:
            An ANSI color code to control the colour of the output.  `colored` is a dependency of this library and
            provides many useful constants in its `fore`, `back` and `style` packages.
        :type text_colour: str
        :param name: The name of the Adapter, used in the startup banner
        :type name: str
        :param source_name: The name of the data source
        :param has_data_catalog:
            Whether to provide a mechanism to notify a data catalogue of data source updates
        :param data_catalog_sink:
            The sink to write data catalogue updates to
        """

        super().__init__(target, text_colour=text_colour, reporting_batch_size=reporting_batch_size,
                         action="Manual Adapter", name=name, dataset=dataset,
                         has_reporter=has_reporter, reporter_sink=reporter_sink,
                         has_error_handler=has_error_handler, error_handler=error_handler,
                         disable_metrics=disable_metrics, has_data_catalog=has_data_catalog,
                         data_catalog_sink=data_catalog_sink)

    def reporter_kwargs(self):
        return {
            'action_name': self.name,
            'target_name': self.target.get_sink_name(),
            'target_type': 'topic',
            'source_name': self.dataset.title,
            'source_type': self.dataset.source_mime_type,
            'action': "adapter",
            'action_id': self.generate_id(),
            'sink': self.reporter_sink,
        }

    def run(self):
        """
        Runs the adapter

        This merely starts the adapter and the caller must then read input records from their data source (which the
        caller is managing) and call the `send()` method to produce output records.

        When the caller has finished producing records they should call `finished()` to indicate this.
        """
        self.display_startup_banner()

        self.print_coloured("Waiting for data from " + self.dataset.title +
                            " - will write out to " + str(self.target))

        if self.reporter is not None:
            self.reporter.run()
            self.print_coloured(f"Telicent Live Reporter registered to send heartbeats to {self.reporter.sink}")

        self.started()

    def finished(self) -> None:
        self.target.close()
        super().finished()

    def aborted(self) -> None:
        self.target.close()
        super().aborted()


class AutomaticAdapter(BaseAdapter):
    """
    An adapter is an action for importing data to a Data Sink.

    This differs from a `Mapper` in that the data source is managed entirely by the caller.  It also differs from the
    manual `Adapter` in that rather than the caller explicitly sending records to the data sink they instead provide a
    `RecordAdapter` function that provides an iterable of records to output to the sink.  The `run()` method simply
    iterates over the records provided by this function and sends them to the sink.

    If code can be written to use an `AutomaticAdapter` it may be better to rewrite it to use a `Mapper` and provide an
    implementation of `DataSource` instead since coding the action that way will be more resilient.  This is because the
    `DataSource` interface provides features like context management and source closure that using a bare generator
    function cannot do as easily.
    """

    def __init__(self, adapter_function: RecordAdapter, target: DataSink = None, dataset=None, name: str = None,
                 text_colour=Fore.light_cyan, reporting_batch_size=DEFAULT_REPORTING_BATCH_SIZE,
                 has_reporter: bool = True, reporter_sink=None,
                 has_error_handler: bool = True, error_handler=None, disable_metrics: bool = False,
                 has_data_catalog: bool = True, data_catalog_sink = None, **adapter_args):
        """
        Creates a new automatic adapter that imports data into a data sink.

        :param target: A sink for the data
        :type target: DataSink
        :param adapter_function:
            An adapter function that is a generator function that provides an iterable of records that want to be output
            to the provided data sink.
        :param text_colour:
            An ANSI color code to control the colour of the output.  `colored` is a dependency of this library and
            provides many useful constants in its `fore`, `back` and `style` packages.
        :type text_colour: str
        :param name: The name of the Adapter
        :type name: str
        :param source_name: The name of the data source, used in the startup banner
        :param adapter_args:
            Additional keyword arguments to pass to the adapter_function when calling it, the adapter_function must take
            keyword arguments for this to work
        :param has_data_catalog:
            Whether to provide a mechanism to notify a data catalogue of data source updates
        :param data_catalogue_sink:
            The sink to write data catalog updates to
        """
        self.adapter_function = adapter_function
        self.adapter_args = adapter_args

        if adapter_function is None:
            raise ValueError('Adapter Function cannot be None')
        validate_callable_protocol(adapter_function, RecordAdapter)
        super().__init__(target, action="Automatic Adapter", name=name, dataset=dataset,
                         text_colour=text_colour, reporting_batch_size=reporting_batch_size,
                         has_reporter=has_reporter, reporter_sink=reporter_sink, disable_metrics=disable_metrics,
                         has_error_handler=has_error_handler, error_handler=error_handler,
                         has_data_catalog=has_data_catalog, data_catalog_sink=data_catalog_sink)

    def reporter_kwargs(self):
        return {
            'action_name': self.name,
            'target_name': self.target.get_sink_name(),
            'target_type': 'topic',
            'source_name': self.dataset.title,
            'source_type': self.dataset.source_mime_type,
            'action': "adapter",
            'action_id': self.generate_id(),
            'sink': self.reporter_sink,
        }

    def is_automatic(self) -> bool:
        return True

    def __invoke_adapter__(self) -> Iterable[Record]:
        if self.adapter_args:
            return self.adapter_function(**self.adapter_args)
        else:
            return self.adapter_function()

    def run(self) -> None:
        """
        Runs the adapter
        """
        self.display_startup_banner()
        self.print_coloured(f"Waiting for data from {self.dataset.title} - will write out to {self.target}",
                            flush=True)

        if self.reporter is not None:
            self.reporter.run()
            self.print_coloured(f"Telicent Live Reporter registered to send heartbeats to {self.reporter.sink}")

        try:
            self.started()
            with self.target:
                for _, record in enumerate(self.__invoke_adapter__()):

                    with self.tracer.start_as_current_span("process record") as tracer_span:
                        carrier: dict = {}
                        TraceContextTextMapPropagator().inject(carrier)

                        with self.tracer.start_as_current_span("prepare headers"):
                            request_id = f'{self.target.get_sink_name()}:{str(uuid.uuid4())}'

                            tracer_span.set_attribute("record.exec_path", self.generated_id)
                            tracer_span.set_attribute("record.request_id", request_id)

                            default_headers = [
                                ('Exec-Path', self.generated_id),
                                ('Request-Id', request_id),
                                ('traceparent', carrier.get('traceparent', '')),
                                ('Data-Source-Name', self.dataset.title),
                                ('Data-Source-Type', self.dataset.source_mime_type),
                            ]
                            record = RecordUtils.add_headers(record, default_headers)

                        with self.tracer.start_as_current_span("send to kafka"):
                            self.target.send(record)

                        self.record_processed()
                        self.record_output()
            self.finished()
        except KeyboardInterrupt:
            self.update_status(Status.TERMINATED)
            self.aborted()
        except Exception as e:
            print()
            self.send_exception(e)
            self.update_status(Status.ERRORING)
            self.print_coloured("ERROR: Unexpected error during processing, is your adapter function faulty?")
            self.aborted()
            raise
