from __future__ import annotations

from colored import Fore
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from telicent_lib.action import DEFAULT_REPORTING_BATCH_SIZE, InputAction
from telicent_lib.exceptions import DLQException
from telicent_lib.records import RecordProjector, RecordUtils
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


class Projector(InputAction):
    """
    A projector is an action that reads from a data source and projects the data to some output location.

    This differs from a `Mapper` in that the data output is managed entirely by the caller via their provided projection
    function.
    """

    def __init__(self, projector_function: RecordProjector, target_store: str, source: DataSource | None = None,
                 target_type: str = None, text_colour: str =  Fore.green,
                 reporting_batch_size: int = DEFAULT_REPORTING_BATCH_SIZE, name: str = None, has_reporter: bool = True,
                 reporter_sink=None,
                 has_error_handler: bool = True, error_handler=None, **projector_args):
        """
        Creates a new projector

        :param source: The Data source to read from
        :type source: DataSource
        :param projector_function:
            A projector function that processes the input records and projects them to the desired output.
        :type projector_function: RecordProjector
        :param text_colour:
            An ANSI color code to control the colour of the output.  `colored` is a dependency of this library and
            provides many useful constants in its `fore`, `back` and `style` packages.
        :type text_colour: str
        :param reporting_batch_size: How often to report progress expressed in terms of number of records
        :type reporting_batch_size: int
        :param projector_args:
            Additional arguments to pass to the projector_function when calling it.  The projector_function must take
            keyword arguments for this to work
        """

        self.target_store = target_store
        self.target_type = target_type

        super().__init__(
            source=source, text_colour=text_colour, reporting_batch_size=reporting_batch_size, name=name,
            action="Projector", has_reporter=has_reporter, reporter_sink=reporter_sink,
            has_error_handler=has_error_handler, error_handler=error_handler
        )

        if projector_function is None:
            raise ValueError('Projection Function cannot be None')
        validate_callable_protocol(projector_function, RecordProjector)
        self.projector_function = projector_function
        self.projector_args = projector_args

    def reporter_kwargs(self):
        return {
            'action_name': self.name,
            'source_name': self.source.get_source_name(),
            'source_type': 'topic',
            'target_name': self.target_store,
            'target_type': self.target_type,
            'action': "projector",
            'action_id': self.generate_id(),
            'sink': self.reporter_sink,
        }

    def run(self):
        """
        Runs the projector.

        This fully manages the input, provided that the configured projection function manages the output the caller
        need only call this.
        """
        self.display_startup_banner()
        self.print_coloured("Waiting for data from " + str(self.source) +
                            " - will write out to " + self.target_store)
        if self.reporter is not None:
            self.reporter.run()
            self.print_coloured(f"Telicent Live Reporter registered to send heartbeats to {self.reporter.sink}")
        with self.source:
            try:
                self.started()
                self.__print_source_status__(self.source)
                for _, record in enumerate(self.source.data()):
                    try:
                        traceparent = list(RecordUtils.get_headers(record, 'traceparent'))[-1]
                    except IndexError:
                        traceparent = None
                    carrier = {"traceparent": traceparent}
                    ctx = TraceContextTextMapPropagator().extract(carrier)
                    with self.tracer.start_as_current_span("process record", context=ctx) as tracer_span:
                        self.record_read()
                        try:
                            input_request_id = list(RecordUtils.get_headers(record, 'Request-Id'))[-1]
                        except IndexError:
                            pass
                        else:
                            tracer_span.set_attribute("record.input_request_id", input_request_id)
                        with self.tracer.start_as_current_span("projector function"):
                            try:
                                if self.projector_args:
                                    self.projector_function(record, **self.projector_args)
                                else:
                                    self.projector_function(record)
                            except DLQException as e:
                                self.send_dlq_record(record, str(e))
                                self.record_processed()
                                continue

                    self.record_processed()
                self.finished()
            except KeyboardInterrupt:
                self.__print_source_status__(self.source)
                self.update_status(Status.TERMINATED)
                self.aborted()
            except Exception as e:
                print()
                self.send_exception(e)
                self.__print_source_status__(self.source)
                self.update_status(Status.ERRORING)
                self.print_coloured("ERROR: Unexpected error during processing, is your projector function faulty?")
                self.aborted()
                raise
