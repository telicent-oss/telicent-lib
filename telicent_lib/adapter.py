import uuid
from typing import Iterable, Union

from colored import fore
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from telicent_lib.access import EDHModel
from telicent_lib.action import DEFAULT_REPORTING_BATCH_SIZE, OutputAction
from telicent_lib.records import Record, RecordAdapter, RecordUtils
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


class Adapter(OutputAction):
    """
    An adapter is an action for importing data to a Data Sink.

    This differs from a `Mapper` in that the data source is managed entirely by the caller who must read the data source
    themselves, transform the records and call the `send()` method of the adapter to send records to the data sink.
    """

    def __init__(self, target: DataSink, text_colour=fore.LIGHT_CYAN, reporting_batch_size=DEFAULT_REPORTING_BATCH_SIZE,
                 name: str = None, source_name: str = None, source_type: str = None, has_reporter: bool = True,
                 reporter_sink=None, has_error_handler: bool = True, error_handler=None, disable_metrics: bool = False):
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
        """
        self.source_name = source_name
        self.source_type = source_type

        super().__init__(target, text_colour=text_colour, reporting_batch_size=reporting_batch_size,
                         action="Manual Adapter", name=name, has_reporter=has_reporter, reporter_sink=reporter_sink,
                         has_error_handler=has_error_handler, error_handler=error_handler,
                         disable_metrics=disable_metrics)

    def reporter_kwargs(self):
        return {
            'action_name': self.name,
            'target_name': self.target.get_sink_name(),
            'target_type': 'topic',
            'source_name': self.source_name,
            'source_type': self.source_type,
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

        if self.source_name is not None:
            self.print_coloured("Waiting for data from " + self.source_name +
                                " - will write out to " + str(self.target))
        else:
            self.print_coloured("Waiting for data - will write out to " + str(self.target))

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


class AutomaticAdapter(OutputAction):
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

    def __init__(self, target: DataSink, adapter_function: RecordAdapter,
                 text_colour=fore.LIGHT_CYAN, reporting_batch_size=DEFAULT_REPORTING_BATCH_SIZE,
                 name: str = None, source_name: str = None, source_type: str = None, has_reporter: bool = True,
                 reporter_sink=None, has_error_handler: bool = True, error_handler=None,
                 policy_information: Union[dict, None] = None,
                 **adapter_args):
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
        """
        self.adapter_function = adapter_function
        self.adapter_args = adapter_args
        self.source_name = source_name
        self.source_type = source_type
        self.policy_information = policy_information
        if adapter_function is None:
            raise ValueError('Adapter Function cannot be None')
        validate_callable_protocol(adapter_function, RecordAdapter)
        super().__init__(target, text_colour=text_colour, reporting_batch_size=reporting_batch_size,
                         action="Automatic Adapter", name=name, has_reporter=has_reporter, reporter_sink=reporter_sink,
                         has_error_handler=has_error_handler, error_handler=error_handler)

    def reporter_kwargs(self):
        return {
            'action_name': self.name,
            'target_name': self.target.get_sink_name(),
            'target_type': 'topic',
            'source_name': self.source_name,
            'source_type': self.source_type,
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
        if self.source_name is not None:
            self.print_coloured(f"Waiting for data from {self.source_name} - will write out to {self.target}",
                                flush=True)
        else:
            self.print_coloured(f"Waiting for data - will write out to {self.target}", flush=True)
        print("")
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
                                ('traceparent', carrier.get('traceparent', ''))
                            ]

                            if self.policy_information:
                                edh_model = EDHModel(**self.policy_information)
                                security_label = edh_model.build_security_labels()
                                default_headers.append(
                                    ('policyInformation', {'EDH': edh_model.model_dump()}),
                                )
                                default_headers.append(
                                    ('Security-Label', security_label)
                                )

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
