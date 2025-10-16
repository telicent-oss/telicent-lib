from __future__ import annotations

import logging
import sys
import time
from collections.abc import Iterable

from colored import Colored, Fore, Style
from opentelemetry import metrics, trace
from opentelemetry.metrics import CallbackOptions, Observation

from telicent_lib.config import Configurator
from telicent_lib.errors import PrintErrorHandler, auto_discover_error_handler
from telicent_lib.records import Record, RecordUtils
from telicent_lib.reporter import Reporter
from telicent_lib.sinks import DataSink, KafkaSink
from telicent_lib.sources import DataSource, KafkaSource
from telicent_lib.status import Status

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


def __calculate_elapsed__(start: float | None) -> float | None:
    """
    Calculates the elapsed time

    :param start: Start time
    :return: Elapsed time
    """
    if start is None:
        return None
    return time.perf_counter() - start


def __calculate_rate__(count: int, elapsed: float | None) -> float:
    """
    Calculates the processing rate

    :param count: Count of records processed
    :param elapsed: Elapsed time
    :return: Processing Rate expressed as records/seconds
    """
    if elapsed is not None and elapsed > 0:
        return count / elapsed
    else:
        return count


DEFAULT_REPORTING_BATCH_SIZE: int = 25000
"""The default reporting batch size used by actions"""


class Action:
    """Represents an action that is executed on the Telicent Core Platform"""

    def __init__(
            self, text_colour: str = Fore.light_gray, reporting_batch_size: int = DEFAULT_REPORTING_BATCH_SIZE,
            action: str = None, name: str = None, has_error_handler: bool = True, error_handler=None,
            has_reporter: bool = True, reporter_sink=None, disable_metrics: bool = False
         ):
        """
        Creates a new instance of an Action

        :param text_colour:
            Specifies a colour for the text, this should be in the form of the ANSI Control Code for the desired colour.
            `colored` is a dependency of this library and provides many useful constants in its `fore`, `back` and
            `style` packages.
        :type text_colour: str
        :param reporting_batch_size:
            Specifies the batch size used for reporting progress i.e. how often the action will report its progress.
            This is specified in terms of number of records, so a value of 10,000 means that the progress is reported
            every 10,000 records.  A higher value is generally better as otherwise the action will waste a bunch of time
            and IO effort reporting too frequently.
        :type reporting_batch_size: int
        :param action: Provides the kind of action, this will be shown in the startup banner
        :type action: str
        :param name:
            Provides a more specific name for the action, this should detail what the specific implementation is doing.
        :type name: str
        """
        # Configure colourised output, this includes detecting whether we are running on a TTY
        # If not on a TTY then we disable colourisation UNLESS the environment explicitly enables it
        self.include_error_handler = has_error_handler
        self.text_colour = text_colour
        self.colors_enabled = self.text_colour is not None and (sys.stdout.isatty() or Colored.enabled())
        if not self.colors_enabled:
            print("Detected not a TTY (or no colour provided), disabled colourised output")
        self.reporter_sink = reporter_sink
        self.include_reporter = has_reporter
        self.reporting_batch_size = reporting_batch_size
        self.action_type = action
        self.name = name
        self.startup_banner_displayed = False
        self.batch_timer: float | None = None
        self.total_timer: float | None = None
        self.counter: int = 0
        self.read_counter: int = 0
        self.output_counter: int = 0
        self.expected: int = 0
        self.error_count: int = 0
        self.last_report_at: int = 0
        self.next_batch_boundary: int = reporting_batch_size
        self.reporter: Reporter | None = None

        try:
            self.generated_id: str = self.generate_id()
        except NotImplementedError:
            # Action has been initialised directly
            pass

        if self.include_error_handler and error_handler is None:
            error_handler_class = auto_discover_error_handler()
            generated_id = self.generate_id()
            try:
                self.error_handler = error_handler_class(generated_id)
            except ValueError:
                print("Error Handler defaulting to print")
                self.error_handler = PrintErrorHandler(generated_id)
        elif self.include_error_handler:
            self.error_handler = error_handler
        else:
            self.error_handler = None

        if self.include_reporter:
            self.reporter = Reporter(**self.reporter_kwargs())

        self.tracer = trace.get_tracer(__name__)
        self.disable_metrics = disable_metrics
        if not self.disable_metrics:
            action_type = self.reporter_kwargs()['action']
            self.meter = metrics.get_meter(self.telemetry_id)

            self.meter.create_observable_gauge(
                name=f"{action_type}.items.processed_rate",
                description="The number of items the component processes per second",
                callbacks=[self.__get_items_processed_rate__],
            )

            self.meter.create_observable_gauge(
                name=f"{action_type}.items.output_rate",
                description="The number of items the component outputs per second",
                callbacks=[self.__get_items_output_rate__],
            )

            self.records_error_counter = self.meter.create_counter(
                f"{action_type}.items.error_total",
                description="The number of errors encountered by the component",
            )

            self.records_dlq_counter = self.meter.create_counter(
                f"{action_type}.items.dlq_total",
                description="The number of messages sent to the dead letter queue by the component",
            )

            self.records_read_counter = self.meter.create_counter(
                f"{action_type}.items.read",
                description="The count of records read",
            )

            self.processed_metric_timer: float | None = None
            self.processed_metric_counter: int = 0
            self.records_processed_counter = self.meter.create_counter(
                f"{action_type}.items.processed",
                description="The count of records processed",
            )

            self.output_metric_timer: float | None = None
            self.output_metric_counter: int = 0
            self.records_output_counter = self.meter.create_counter(
                f"{action_type}.items.output",
                description="The count of records output",
            )

        self.dlq_target: DataSink | None = None

    def set_dlq_target(self, target: DataSink):
        self.dlq_target = target

    def send_dlq_record(self, record: Record, dlq_reason: str):
        if self.dlq_target is not None:
            record = RecordUtils.add_headers(record, [('Dead-Letter-Reason', dlq_reason)])
            self.dlq_target.send(record)
            if not self.disable_metrics:
                self.records_dlq_counter.add(1)
        else:
            error_message = 'Unable to send record to DLQ as dlq_target has not been set.'
            logger.error(error_message)
            raise RuntimeError(error_message)

    @property
    def telemetry_id(self):
        return f"telicent_lib.{self.action_type}.{self.generate_id()}"

    def __get_items_processed_rate__(self, options: CallbackOptions) -> Iterable[Observation]:
        total_elapsed = __calculate_elapsed__(self.processed_metric_timer)
        observation = Observation(
            __calculate_rate__(self.processed_metric_counter, total_elapsed), {"item.type": "record"}
        )
        self.processed_metric_timer = time.perf_counter()
        self.processed_metric_counter = 0
        return [observation]

    def __get_items_output_rate__(self, options: CallbackOptions) -> Iterable[Observation]:
        total_elapsed = __calculate_elapsed__(self.output_metric_timer)
        observation = Observation(
            __calculate_rate__(self.output_metric_counter, total_elapsed), {"item.type": "record"}
        )
        self.output_metric_timer = time.perf_counter()
        self.output_metric_counter = 0
        return [observation]

    def __get_errors__(self, options: CallbackOptions) -> Iterable[Observation]:
        return [Observation(self.error_count, {"item.type": "record"})]

    def reporter_kwargs(self):
        raise NotImplementedError()

    def generate_id(self):
        raise NotImplementedError()

    def update_status(self, status: Status):
        if self.include_reporter and self.reporter is not None:
            self.reporter.set_status(status)

    def display_startup_banner(self) -> None:
        """Displays a startup banner for the action

        Should be called once prior to the actions actual logic.  If called multiple times then subsequent calls will
        produce no output.

        If the caller is calling the `run()` method then this will be called automatically.
        """
        if self.startup_banner_displayed:
            return
        self.startup_banner_displayed = True

        horizontal_line = "".ljust(80, '-')
        empty_line = "|".ljust(79) + "|"

        self.print_coloured(horizontal_line)
        self.print_coloured(empty_line)
        self.print_coloured("|" + "TELICENT CORE".center(78) + "|")
        if self.action_type is not None and len(self.action_type) > 0:
            self.print_coloured("|" + self.action_type.center(78) + "|")
        if self.name is not None and len(self.name) > 0:
            self.print_coloured("|" + self.name.center(78) + "|")
        self.print_coloured(empty_line)
        self.print_coloured(horizontal_line, True)

    def print_coloured(self, line: str, flush=False, end='\n') -> None:
        """
        Prints a line of text in the colour configured for this action.

        If colourisation is disabled then just prints the text as-is.

        :param line
            The line of text to print.
        :type line: str
        :param flush: Whether to forcibly flush the stream.
        :type flush: bool
        :param end: The end character to add to the output, default is the newline character.
        :type end: str
        """

        if self.colors_enabled:
            print(self.text_colour + line + Style.reset, end=end, flush=flush)
        else:
            print(line, end=end, flush=flush)

    def is_automatic(self) -> bool:
        """
        Returns whether an action is automatic i.e. if the caller merely need call the `run()` method or if the caller
        needs to code further logic themselves
        :return: True if an automatic action, False if not
        :rtype: bool
        """
        raise NotImplementedError

    def started(self) -> None:
        """
        Tells the action that it has been started

        If caller is using the `run()` method then this will be called automatically.
        """
        if self.batch_timer is not None:
            raise Exception('Action has already been started')
        if self.total_timer is not None:
            raise Exception('Action has already been started')

        self.total_timer = time.perf_counter()
        self.batch_timer = self.total_timer
        self.output_metric_timer = self.total_timer
        self.processed_metric_timer = self.total_timer
        self.counter = 0
        self.print_coloured("Started work...")

    def expect_records(self, expected: int) -> None:
        """
        Sets the total number of records that this action should expect to process.

        This can be used if the action knows the amount of input records to be processed and will be used to provide
        progress percentages as part of progress reporting.
        :param expected: Expected number of records
        """
        self.display_startup_banner()
        self.expected = expected
        if self.expected > 0:
            self.print_coloured(f"Expecting to process {self.expected:,} records")

    def run(self) -> None:
        """
        Runs the action

        If this is an automatic action then the caller merely need call this and the action will proceed automatically.
        If this isn't an automatic action then the caller should call this and then perform further logic, see
        individual Action subclasses for more specific documentation.
        """
        raise RuntimeError('run() is not implemented')

    def record_processed(self) -> None:
        """
        Tells the action that a record has been processed.

        This is used to provide automated progress reporting based upon the configured reporting batch size for the
        Action.
        """
        with self.tracer.start_as_current_span('acknowledge processed') as tracer_span:
            self.counter += 1
            if not self.disable_metrics:
                self.records_processed_counter.add(1)
                self.processed_metric_counter += 1
            tracer_span.set_attribute("action.counter", self.counter)
            if self.reporting_batch_size > 0 and self.counter % self.reporting_batch_size == 0:
                self.report_progress()
            elif self.counter > self.next_batch_boundary:
                self.report_progress()

    def record_read(self) -> None:
        """
        Tells the action that a record has been output.
        """
        with self.tracer.start_as_current_span('acknowledge read'):
            if not self.disable_metrics:
                self.records_read_counter.add(1)
            self.read_counter += 1

    def record_output(self) -> None:
        """
        Tells the action that a record has been output.
        """
        with self.tracer.start_as_current_span('acknowledge output'):
            if not self.disable_metrics:
                self.records_output_counter.add(1)
                self.output_metric_counter += 1
            self.output_counter += 1

    def records_processed(self, count: int) -> None:
        """
        Tells the action that multiple records have been processed.  This should be called if the caller is batching up
        their record processing.

        This is used to provide automated progress reporting based upon the configured reporting batch size for the
        Action.
        :param count: Number of records processed
        """
        self.counter += count
        if self.reporting_batch_size > 0 and self.counter % self.reporting_batch_size == 0:
            self.report_progress()
        elif self.counter > self.next_batch_boundary:
            self.report_progress()

    def report_progress(self) -> None:
        """
        Reports the current progress by printing it out
        """
        # Don't report progress at the same point multiple times
        # with self.tracer.start_as_current_span("report progress") as tracer_span:
        if self.last_report_at == self.counter:
            return

        last = self.counter - self.last_report_at
        self.last_report_at = self.counter
        self.next_batch_boundary += self.reporting_batch_size

        batch_elapsed = __calculate_elapsed__(self.batch_timer)
        total_elapsed = __calculate_elapsed__(self.total_timer)
        batch_rate = __calculate_rate__(last, batch_elapsed)
        total_rate = __calculate_rate__(self.counter, total_elapsed)
        line = ""
        if self.expected > 0:
            percentage = (self.counter / self.expected) * 100
            line += f" [{percentage:.2f}%]"
        line += f" {self.counter:,} records processed.  Last {last:,} records took {batch_elapsed:,.2f} seconds. "
        line += f"Batch rate was {batch_rate:,.2f} records/seconds. "
        line += f"Overall rate is {total_rate:,.2f} records/seconds."
        self.print_coloured(line)
        self.batch_timer = time.perf_counter()

    def aborted(self) -> None:
        """
        Tells the action that it has been aborted.

        This should be called when handling interrupts or cancellations.
        """
        if self.counter % self.reporting_batch_size != 0:
            self.report_progress()
        print("")

        elapsed = __calculate_elapsed__(self.total_timer)
        rate = __calculate_rate__(self.counter, elapsed)
        self.print_coloured(
            f"Aborted!  Processed {self.counter:,} records in {elapsed:,.2f} seconds at {rate:,.2f} records/seconds")
        if self.reporter is not None:
            self.reporter.stop_heartbeat()
            self.print_coloured(f"Telicent Live Reporter unregistered from {self.reporter.sink}")

        if self.error_handler is not None:
            self.error_handler.close()

    def finished(self) -> None:
        """
        Tells the action that it has finished.

        If the caller is using the `run()` method then this will be called automatically.
        """
        if self.batch_timer is None:
            raise Exception('Action has not been started')

        # If we did not finish exactly on a reporting batch size report the stats for the final batch
        if self.counter % self.reporting_batch_size != 0:
            self.report_progress()
        print("")

        # If we were told how many records were expected note if this was incorrect
        # noinspection PyChainedComparisons
        if self.expected > 0 and self.counter != self.expected:
            self.print_coloured(
                f"Expected number of records was incorrect, expected {self.expected:,} but processed {self.counter:,}")
            print("")

        # Display the final processing rate
        elapsed = __calculate_elapsed__(self.total_timer)
        rate = __calculate_rate__(self.counter, elapsed)
        self.print_coloured(
            f"Finished Work, processed {self.counter:,} record{'s' if self.counter != 1 else ''} in {elapsed:,.2f} "
            f"seconds at {rate:,.2f} records/seconds and "
            f"encountered {self.error_count:,} error{'s' if self.error_count != 1 else ''}.")

        # Reset the action progress counters
        self.__reset_counters__()
        if self.reporter is not None:
            self.update_status(Status.COMPLETED)
            self.reporter.stop_heartbeat()
            self.print_coloured(f"Telicent Live Reporter unregistered from {self.reporter.sink}")

    def send_error(self, error, error_type, level):
        if not self.disable_metrics:
            self.records_error_counter.add(1)
        self.error_count += 1
        if self.include_error_handler:
            self.error_handler.send_error(error, error_type, level, self.counter)

    def send_exception(self, e):
        if not self.disable_metrics:
            self.records_error_counter.add(1)
        self.error_count += 1
        if self.include_error_handler:
            self.error_handler.send_exception(e, counter=self.counter)

    def __reset_counters__(self) -> None:
        """
        Resets the internal progress counters and timers
        """
        self.expected = 0
        self.counter = 0
        self.error_count = 0
        self.total_timer = None
        self.batch_timer = None
        self.next_batch_boundary = self.reporting_batch_size

    def __print_source_status__(self, source: DataSource) -> None:
        """
        Prints the status of the source, i.e. the number of records available, if the source is able to provide it.  If
        the given source is unable to provide the number of remaining records then nothing is printed.

        :param source: Data source
        """
        logger.debug('Getting source status')
        remaining = source.remaining()
        logger.debug(f'remaining: {remaining}')
        if remaining is not None:
            if remaining == 0:
                self.print_coloured(f"Source {source} has no further records available")
            else:
                self.print_coloured(f"Source {source} has {remaining:,} records remaining")


class OutputAction(Action):
    def __init__(self, target: DataSink | None, text_colour: str = Fore.light_cyan,
                 reporting_batch_size: int = DEFAULT_REPORTING_BATCH_SIZE,
                 action: str = None, name: str = None, has_reporter: bool = True, reporter_sink=None,
                 has_error_handler: bool = True, error_handler=None, disable_metrics: bool = False):
        """
        Creates a new instance of an Action that produces Output

        The action likely has some input but that input is not represented using our DataSource API

        :param target: Provides a Data Sink for this action
        :type target: DataSink
        :param text_colour:
            Specifies a colour for the text, this should be in the form of the ANSI Control Code for the desired colour
        :type text_colour: str
        :param reporting_batch_size:
            Specifies the batch size used for reporting progress i.e. how often the action will report its progress.
            This is specified in terms of number of records, so a value of 10,000 means that the progress is reported
            every 10,000 records.
        :type reporting_batch_size: int
        :param action: Provides the kind of action, this will be shown in the startup banner
        :type action: str
        :param name:
            Provides a more specific name for the action, this should detail what the specific implementation is doing.
        :type name: str
        """
        if target is None:
            config = Configurator()
            target = KafkaSink(topic=config.get('TARGET_TOPIC'))

        if not isinstance(target, DataSink):
            raise TypeError('Did not receive a Data Sink as required')
        self.target = target

        super().__init__(text_colour=text_colour, reporting_batch_size=reporting_batch_size,
                         action=action, name=name, has_reporter=has_reporter, reporter_sink=reporter_sink,
                         has_error_handler=has_error_handler, error_handler=error_handler,
                         disable_metrics=disable_metrics)

    def send(self, record: Record):
        """
        Sends data to the configured data sink for this action and updates progress counters

        :param record: Record to send as output
        :type record: Record
        """
        self.target.send(record)
        self.record_processed()

    def is_automatic(self) -> bool:
        return False

    def generate_id(self):
        if self.name is not None:
            return self.name.replace(' ', "-")
        name = ''
        if self.target is not None:
            name = f'{name}-to-{self.target}'
        return f'{self.action_type}{name}'


class InputAction(Action):
    def __init__(self, source: DataSource | None = None, text_colour: str = Fore.green,
                 reporting_batch_size: int = DEFAULT_REPORTING_BATCH_SIZE, action: str = None, name: str = None,
                 has_reporter: bool = True, reporter_sink=None, has_error_handler: bool = True, error_handler=None,
                 disable_metrics: bool = False):
        """
        Creates a new instance of an Action that takes Input

        This action likely has some output but that output is not represented using our DataSink API

        :param source: Provides a Data Source for this action
        :type source: DataSource
        :param text_colour:
            Specifies a colour for the text, this should be in the form of the ANSI Control Code for the desired colour
        :type text_colour: str
        :param reporting_batch_size:
            Specifies the batch size used for reporting progress i.e. how often the action will report its progress.
            This is specified in terms of number of records, so a value of 10,000 means that the progress is reported
            every 10,000 records.
        :type reporting_batch_size: int
        :param action: Provides the kind of action, this will be shown in the startup banner
        :type action: str
        :param name:
            Provides a more specific name for the action, this should detail what the specific implementation is doing.
        :type name: str
        """
        config = Configurator()
        if source is None:
            source = KafkaSource(config.get('SOURCE_TOPIC'))
        if not isinstance(source, DataSource):
            raise TypeError('Did not receive a Data Source as required')
        self.source = source

        super().__init__(
            text_colour=text_colour, reporting_batch_size=reporting_batch_size, action=action, name=name,
            has_reporter=has_reporter, reporter_sink=reporter_sink,
            has_error_handler=has_error_handler, error_handler=error_handler, disable_metrics=disable_metrics
        )

        config = Configurator()
        if config.get('AUTO_ENABLE_DLQ', default='false', converter=Configurator.string_to_bool):
            if isinstance(source, KafkaSource):
                self.set_dlq_target(self.init_dlq_target(source))
            else:
                logger.warning(
                    'Dead letter queue sink can only be automatically initialised when the action\'s source is a '
                    'KafkaSource. To provide a dead letter queue sink manually, call `set_dql_target(target: DataSink)'
                )

    @staticmethod
    def init_dlq_target(source: KafkaSource):
        """
        Convenience function for when using a KafkaSource, to initialise a DLQ sink
        targeting a topic based on the action's source's topic.
        """
        return KafkaSink(f'{source.topic}.dlq')

    def generate_id(self):
        if self.name is not None:
            return self.name.replace(' ', "-")
        name = ''
        if self.source is not None:
            name = f'-from-{self.source}'
        return f'{self.action_type}{name}'

    def is_automatic(self) -> bool:
        return True


class InputOutputAction(OutputAction):
    def __init__(self, source: DataSource| None, target: DataSink | None, text_colour: str = Fore.yellow,
                 reporting_batch_size: int = DEFAULT_REPORTING_BATCH_SIZE,
                 action: str = None, name: str = None, has_reporter: bool = True, reporter_sink=None,
                 has_error_handler: bool = True, error_handler=None, disable_metrics: bool = False):
        """
        Creates a new instance of an Action that has both Input and Output

        :param source: Provides a Data Source for this action
        :type source: DataSource
        :param target: Provides a Data Sink for this action
        :type target: DataSink
        :param text_colour:
            Specifies a colour for the text, this should be in the form of the ANSI Control Code for the desired colour
        :type text_colour: str
        :param reporting_batch_size:
            Specifies the batch size used for reporting progress i.e. how often the action will report its progress.
            This is specified in terms of number of records, so a value of 10,000 means that the progress is reported
            every 10,000 records.
        :type reporting_batch_size: int
        :param action: Provides the kind of action, this will be shown in the startup banner
        :type action: str
        :param name:
            Provides a more specific name for the action, this should detail what the specific implementation is doing.
        :type name: str
        """
        config = Configurator()
        if source is None:
            source = KafkaSource(topic=config.get('SOURCE_TOPIC', required=True))

        self.source = source
        self.records_output = 0
        super().__init__(target=target, text_colour=text_colour, reporting_batch_size=reporting_batch_size,
                         action=action, name=name, has_reporter=has_reporter, reporter_sink=reporter_sink,
                         has_error_handler=has_error_handler, error_handler=error_handler,
                         disable_metrics=disable_metrics)

        if source is None:
            raise ValueError('Data Source cannot be None')
        if not isinstance(source, DataSource):
            raise TypeError('Did not receive a Data Source as required')

        config = Configurator()
        if config.get('AUTO_ENABLE_DLQ', default='false', converter=Configurator.string_to_bool):
            if isinstance(source, KafkaSource):
                self.set_dlq_target(self.init_dlq_target(source))
            else:
                logger.warning(
                    'Dead letter queue sink can only be automatically initialised when the action\'s source is a '
                    'KafkaSource. To provide a dead letter queue sink manually, call `set_dql_target(target: DataSink)'
                )

    @staticmethod
    def init_dlq_target(source: KafkaSource):
        """
        Convenience function for when using a KafkaSource, to initialise a DQL sink
        targeting a topic based on the action's source's topic.
        """
        return KafkaSink(f'{source.topic}.dlq')

    def generate_id(self):
        if self.name is not None:
            return self.name.replace(' ', "-")
        name = ''
        if self.source is not None:
            name = f'-from-{self.source}'
        if self.target is not None:
            name = f'{name}-to-{self.target}'
        return f'{self.action_type}{name}'

    def is_automatic(self) -> bool:
        return True
