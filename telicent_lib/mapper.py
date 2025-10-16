from __future__ import annotations

import logging
import uuid

from colored import Fore
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from telicent_lib.action import DEFAULT_REPORTING_BATCH_SIZE, InputOutputAction
from telicent_lib.config.configurator import Configurator
from telicent_lib.exceptions import DLQException
from telicent_lib.records import RecordMapper, RecordUtils
from telicent_lib.sinks import DataSink
from telicent_lib.sources import DataSource
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


class Mapper(InputOutputAction):
    """
    A mapper is an action that maps between a data source and a data sink.

    A mapper automatically manages both the data source and data sink transforming the input records into output
    records using the provided `map_function`.

    If the data source wants to be managed entirely by the caller then use an `Adapter` instead.

    If the data sink wants to be managed entirely by the caller then use a `Projector` instead.
    """

    def __init__(self, map_function: RecordMapper, source: DataSource | None = None, target: DataSink | None = None,
                 text_colour: str = Fore.yellow,
                 reporting_batch_size: int = DEFAULT_REPORTING_BATCH_SIZE, name: str = None, has_reporter: bool = True,
                 reporter_sink=None, has_error_handler: bool = True, error_handler=None, disable_metrics: bool = False,
                 **map_args):
        """
        Creates a mapper that maps between a data source and a data sink.

        :param source: The Data source to read from
        :type source: DataSource
        :param target: The Data sink to write to
        :type target: DataSink
        :param map_function:
            A map function that transforms the input records into the output records.  The result of this function may
            either be a single Record, or a list of Records.  Thus, a Mapper can be used to express both a map (single
            input to single output) and a flat map (single input to many outputs) operation.
        :type map_function: RecordMapper
        :param text_colour:
            An ANSI color code to control the colour of the output.  `colored` is a dependency of this library and
            provides many useful constants in its `fore`, `back` and `style` packages.
        :type text_colour: str
        :param reporting_batch_size: How often to report progress expressed in terms of number of records
        :type reporting_batch_size: int
        :param map_args:
            Additional arguments to pass to the map_function when calling it.  The map_function must take keyword
            arguments for this to work
        """

        super().__init__(source=source, target=target, text_colour=text_colour,
                         reporting_batch_size=reporting_batch_size, name=name, has_reporter=has_reporter,
                         reporter_sink=reporter_sink, has_error_handler=has_error_handler, error_handler=error_handler,
                         action="Mapper", disable_metrics=disable_metrics)

        if map_function is None:
            raise ValueError('Map Function cannot be None')
        validate_callable_protocol(map_function, RecordMapper)
        self.map_function = map_function
        self.map_args = map_args

    def reporter_kwargs(self):
        return {
            'action_name': self.name,
            'target_name': self.target.get_sink_name(),
            'target_type': 'topic',
            'source_name': self.source.get_source_name(),
            'source_type': 'topic',
            'action': "mapper",
            'action_id': self.generate_id(),
            'sink': self.reporter_sink,
        }

    def run(self):
        """
        Runs the mapper.

        This fully manages all the input and output and the caller need only call this.
        """
        self.display_startup_banner()
        self.print_coloured("Waiting for data from " + str(self.source) +
                            " - will write out to " + str(self.target), flush=True)
        print("")
        if self.reporter is not None:
            self.reporter.run()
            self.print_coloured(f"Telicent Live Reporter registered to send heartbeats to {self.reporter.sink}")
        with self.source:
            try:
                self.started()
                logger.debug('Print source status')
                self.__print_source_status__(self.source)
                with self.target:
                    for _, record in enumerate(self.source.data()):
                        try:
                            traceparent = list(RecordUtils.get_headers(record, 'traceparent'))[-1]
                        except IndexError:
                            traceparent = None
                        carrier = {"traceparent": traceparent}
                        ctx = TraceContextTextMapPropagator().extract(carrier)
                        with self.tracer.start_as_current_span("process record", context=ctx) as tracer_span:
                            carrier = {}
                            TraceContextTextMapPropagator().inject(carrier)
                            self.record_read()
                            tracer_span.set_attribute("record.mapper", str(self.map_function))
                            # The map function may return either a single record or a list of records which we need to
                            # send onto the target sink.  Also, there's the potential that a record should not be mapped
                            # at all in which case None would be returned.
                            with self.tracer.start_as_current_span("map function"):
                                try:
                                    if self.map_args:
                                        output_data = self.map_function(record, **self.map_args)
                                    else:
                                        output_data = self.map_function(record)
                                except DLQException as e:
                                    self.send_dlq_record(record, str(e))
                                    self.record_processed()
                                    continue

                            self.record_processed()
                            with self.tracer.start_as_current_span("process output"):
                                if output_data is not None:
                                    with self.tracer.start_as_current_span("prepare headers"):
                                        output_headers = []
                                        try:
                                            input_request_id = list(RecordUtils.get_headers(record, 'Request-Id'))[-1]
                                        except IndexError:
                                            pass
                                        else:
                                            output_headers.append(('Input-Request-Id', input_request_id))
                                            tracer_span.set_attribute("record.input_request_id", input_request_id)

                                        request_id = f'{self.target.get_sink_name()}:{str(uuid.uuid4())}'

                                        tracer_span.set_attribute("record.exec_path", self.generated_id)
                                        tracer_span.set_attribute("record.request_id", request_id)

                                        output_headers += [
                                            ('Request-Id', request_id),
                                            ('Exec-Path', self.generated_id),
                                            ('traceparent', carrier.get('traceparent', ''))
                                        ]
                                    if isinstance(output_data, list):
                                        for output_record in output_data:
                                            output_record = RecordUtils.add_headers(output_record, output_headers)
                                            self.target.send(output_record)
                                    else:
                                        output_data = RecordUtils.add_headers(output_data, output_headers)
                                        conf = Configurator()
                                        if conf.get("DISABLE_PERSISTENT_HEADERS", "0") != "1" and \
                                                not RecordUtils.has_header(output_data, 'Security-Label') and \
                                                RecordUtils.has_header(record, 'Security-Label'):
                                            label_headers = RecordUtils.get_headers(record, 'Security-Label')
                                            for header_value in label_headers:
                                                output_data = RecordUtils.add_header(
                                                    output_data,
                                                    'Security-Label',
                                                    header_value
                                                )
                                        self.target.send(output_data)
                                    self.record_output()
                self.finished()
            except KeyboardInterrupt:
                self.__print_source_status__(self.source)
                self.update_status(Status.TERMINATED)
                self.aborted()
            except Exception as e:
                self.send_exception(e)
                self.__print_source_status__(self.source)
                self.update_status(Status.ERRORING)
                self.print_coloured("ERROR: Unexpected error during processing, is your map function faulty?")
                self.aborted()
                raise
