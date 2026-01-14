import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from colored import Fore
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from telicent_lib.action import DEFAULT_REPORTING_BATCH_SIZE, InputAction
from telicent_lib.config import Configurator
from telicent_lib.records import Record, RecordUtils
from telicent_lib.sources.kafkaSource import KafkaSource
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

DEFAULT_BATCH_SIZE = 100
DEFAULT_BATCH_TIMEOUT_SECS = 5.0
DEFAULT_STORAGE_RETRY_COUNT = 3


@dataclass
class BatchItem:
    """
    Represents a single item in a batch.
    """

    key: Any
    value: Any
    headers: list[tuple[str, Any]] | None
    partition: int | None
    offset: int | None
    topic: str | None
    timestamp: int | None
    raw: Any

    @property
    def headers_dict(self) -> dict[str, str]:
        """
        Returns headers as a dictionary with string keys and values.

        If a header appears multiple times, the last value wins.
        Bytes values are decoded to UTF-8 strings.
        """
        if self.headers is None:
            return {}

        result: dict[str, str] = {}
        for key, value in self.headers:
            if value is None:
                result[key] = ""
            elif isinstance(value, bytes):
                result[key] = value.decode("utf-8")
            else:
                result[key] = str(value)
        return result


@runtime_checkable
class BatchStorageFunction(Protocol):
    """
    Represents a callable function that stores a batch of items to an external system.
    """

    def __call__(self, batch: list[BatchItem]) -> None:
        """
        Stores a batch of items to an external system.

        :param batch: List of BatchItem objects to store
        :raises Exception: If storage fails
        """
        pass


class BatchingProjector(InputAction):
    """
    A projector that batches records before passing them to a storage function.

    Records are batched up to a maximum size or until a timeout occurs.
    The storage function receives batches of BatchItem objects and is responsible for
    persisting them to the target system.
    """

    def __init__(
        self,
        storage_function: BatchStorageFunction,
        target_store: str,
        source: KafkaSource | None = None,
        target_type: str | None = None,
        text_colour: str | None = Fore.green,
        reporting_batch_size: int = DEFAULT_REPORTING_BATCH_SIZE,
        name: str | None = None,
        has_reporter: bool = True,
        reporter_sink=None,
        has_error_handler: bool = True,
        error_handler=None,
        batch_size: int | None = None,
        batch_timeout_secs: float | None = None,
        storage_retry_count: int | None = None,
        **storage_args,
    ):
        """
        Creates a new BatchingProjector.

        :param storage_function: Function that stores batches of BatchItem objects
        :param target_store: Name of the target store for reporting
        :param source: Data source to read from
        :param target_type: Type of target store for reporting
        :param text_colour: ANSI color code for output
        :param reporting_batch_size: How often to report progress
        :param name: Name of this projector instance
        :param has_reporter: Whether to enable the Telicent Live Reporter
        :param reporter_sink: Sink for the reporter
        :param has_error_handler: Whether to enable error handling
        :param error_handler: Custom error handler
        :param batch_size: Maximum batch size (default from BATCH_SIZE env or 100)
        :param batch_timeout_secs: Batch timeout in seconds (default from BATCH_TIMEOUT_SECS env or 5.0)
        :param storage_retry_count: Number of retries for storage failures (default from STORAGE_RETRY_COUNT env or 3)
        :param storage_args: Additional arguments passed to storage_function
        """
        self.target_store = target_store
        self.target_type = target_type

        super().__init__(
            source=source,
            text_colour=text_colour,
            reporting_batch_size=reporting_batch_size,
            name=name,
            action="BatchingProjector",
            has_reporter=has_reporter,
            reporter_sink=reporter_sink,
            has_error_handler=has_error_handler,
            error_handler=error_handler,
        )

        if storage_function is None:
            raise ValueError("Storage Function cannot be None")

        self.storage_function = storage_function
        self.storage_args = storage_args

        # Load configuration
        conf = Configurator()
        self.batch_size = batch_size or conf.get(
            "BATCH_SIZE", default=DEFAULT_BATCH_SIZE, converter=int
        )
        self.batch_timeout_secs = batch_timeout_secs or conf.get(
            "BATCH_TIMEOUT_SECS", default=DEFAULT_BATCH_TIMEOUT_SECS, converter=float
        )
        self.storage_retry_count = storage_retry_count or conf.get(
            "STORAGE_RETRY_COUNT", default=DEFAULT_STORAGE_RETRY_COUNT, converter=int
        )

        # Internal state for batching
        # The lock protects _batch and _batch_start_time which are accessed by both
        # the main processing loop and the background timeout monitor thread.
        self._batch: list[Record] = []
        self._batch_start_time: float | None = None
        self._lock = threading.Lock()

        # Timeout monitor state - a background thread periodically checks if the
        # batch timeout has elapsed and flushes if needed. This ensures partial
        # batches are flushed during quiet periods when no new records are arriving.
        self._stopped = False
        self._timeout_monitor_thread: threading.Thread | None = None

        # Deferred commit flag - set by background thread after storage, committed by main thread.
        # This avoids calling Kafka commit() from a background thread while the main thread
        # is in consumer.poll(), which would be thread-unsafe.
        self._pending_commit = False

    def reporter_kwargs(self):
        return {
            "action_name": self.name,
            "source_name": self.source.get_source_name(),
            "source_type": "topic",
            "target_name": self.target_store,
            "target_type": self.target_type,
            "action": "batching_projector",
            "action_id": self.generate_id(),
            "sink": self.reporter_sink,
        }

    def _get_record_metadata(self, record: Record) -> dict[str, Any]:
        """Extract Kafka metadata from the raw record if available."""
        metadata: dict[str, Any] = {
            "partition": None,
            "offset": None,
            "topic": None,
            "timestamp": None,
        }

        if record.raw is not None:
            # Try to extract Kafka-specific metadata
            if hasattr(record.raw, "partition"):
                metadata["partition"] = record.raw.partition()
            if hasattr(record.raw, "offset"):
                metadata["offset"] = record.raw.offset()
            if hasattr(record.raw, "topic"):
                metadata["topic"] = record.raw.topic()
            if hasattr(record.raw, "timestamp"):
                ts = record.raw.timestamp()
                if ts is not None and isinstance(ts, tuple) and len(ts) > 1:
                    metadata["timestamp"] = ts[1]
                elif isinstance(ts, int):
                    metadata["timestamp"] = ts

        return metadata

    def _create_batch_items(self, records: list[Record]) -> list[BatchItem]:
        """Create BatchItem objects from records."""
        batch_items = []
        for record in records:
            metadata = self._get_record_metadata(record)
            batch_item = BatchItem(
                key=record.key,
                value=record.value,
                headers=record.headers,
                partition=metadata["partition"],
                offset=metadata["offset"],
                topic=metadata["topic"],
                timestamp=metadata["timestamp"],
                raw=record.raw,
            )
            batch_items.append(batch_item)
        return batch_items

    def _store_batch(self, batch_items: list[BatchItem]) -> list[BatchItem]:
        """
        Attempt to store a batch, with retry logic.

        :param batch_items: Items to store
        :return: List of items that failed to store (empty if all succeeded)
        """
        for attempt in range(self.storage_retry_count):
            try:
                if self.storage_args:
                    self.storage_function(batch_items, **self.storage_args)
                else:
                    self.storage_function(batch_items)
                return []  # Success
            except Exception as e:
                logger.warning(
                    f"Storage attempt {attempt + 1}/{self.storage_retry_count} failed: {e}"
                )
                if attempt < self.storage_retry_count - 1:
                    time.sleep(0.5 * (attempt + 1))  # Backoff

        # All retries failed - try splitting if batch > 1
        if len(batch_items) > 1:
            logger.info(
                f"Splitting batch of {len(batch_items)} for individual processing"
            )
            failed_items = []
            for item in batch_items:
                single_failed = self._store_batch([item])
                failed_items.extend(single_failed)
            return failed_items
        else:
            # Single item failed all retries
            return batch_items

    def _process_batch(self, records: list[Record]) -> None:
        """
        Process a batch of records: create batch items, store, handle failures.
        """
        if not records:
            return

        # Create batch items
        batch_items = self._create_batch_items(records)

        # Attempt to store
        failed_items = self._store_batch(batch_items)

        # Send failed items to DLQ
        for item in failed_items:
            record = Record(
                headers=item.headers, key=item.key, value=item.value, raw=item.raw
            )
            self.send_dlq_record(record, "Storage failed after all retries")

        # Update counters
        successful_count = len(batch_items) - len(failed_items)
        for _ in range(successful_count):
            self.record_processed()

        # Mark that we need to commit offsets. The actual commit is deferred to the
        # main thread to avoid thread-safety issues with the Kafka consumer.
        if successful_count > 0:
            self._pending_commit = True

    def _should_flush_batch(self) -> bool:
        """Check if batch should be flushed due to size or timeout."""
        if len(self._batch) >= self.batch_size:
            return True
        if self._batch_start_time is not None:
            elapsed = time.monotonic() - self._batch_start_time
            if elapsed >= self.batch_timeout_secs:
                return True
        return False

    def _flush_batch(self) -> None:
        """Flush the current batch."""
        with self._lock:
            if not self._batch:
                return
            batch_to_process = self._batch
            self._batch = []
            self._batch_start_time = None

        self._process_batch(batch_to_process)

    def _timeout_monitor(self) -> None:
        """
        Background thread that monitors batch timeout and triggers flush when needed.

        WHY THIS EXISTS:
        The main processing loop blocks on source.data() waiting for the next record.
        For Kafka sources, this can block indefinitely during quiet periods. Without
        this monitor, a partial batch (e.g., 5 records when batch_size=100) would sit
        in memory until a new record arrives - potentially hours or days later.

        HOW IT WORKS:
        This thread wakes every second to check if the batch timeout has elapsed.
        If so, it triggers a flush. The lock ensures thread-safe access to the batch
        state shared between this monitor and the main processing loop.

        The daemon=True flag ensures this thread is automatically terminated when the
        main process exits, preventing hangs during shutdown.
        """
        while not self._stopped:
            time.sleep(1.0)
            if self._stopped:
                break
            with self._lock:
                should_flush = self._should_flush_batch()
            if should_flush:
                self._flush_batch()

    def _start_timeout_monitor(self) -> None:
        """
        Start the background timeout monitor thread.

        Called at the start of run() to ensure timeout-based flushing is active
        throughout the processing loop.
        """
        self._stopped = False
        self._timeout_monitor_thread = threading.Thread(
            target=self._timeout_monitor,
            daemon=True,
            name="BatchingProjector-TimeoutMonitor"
        )
        self._timeout_monitor_thread.start()

    def _stop_timeout_monitor(self) -> None:
        """
        Stop the background timeout monitor thread.

        Called when processing completes (normally, via interrupt, or on error)
        to cleanly shut down the monitor before final flush.
        """
        self._stopped = True
        if self._timeout_monitor_thread is not None:
            self._timeout_monitor_thread.join(timeout=2.0)
            self._timeout_monitor_thread = None

    def _disable_source_auto_commit(self) -> None:
        """
        Disable automatic offset commits on KafkaSource.

        WHY THIS EXISTS:
        By default, KafkaSource commits offsets as records are READ (every commit_interval).
        This creates a data loss risk for batching:
          1. Read 100 records into batch
          2. KafkaSource auto-commits offsets (Kafka thinks records are "done")
          3. Crash before batch is stored
          4. On restart, those 100 records are lost forever

        By disabling auto-commit, we take control of when commits happen. We only
        commit AFTER successfully storing a batch (see _commit_source_offsets).
        """
        self.source.set_auto_commit(False)
        logger.info("Disabled source auto-commit for safe batching")

    def _commit_source_offsets(self) -> None:
        """
        Commit source offsets to Kafka.

        THREAD SAFETY:
        This method must only be called from the main thread. The Kafka consumer
        is not thread-safe, and calling commit() from a background thread while
        the main thread is in consumer.poll() leads to undefined behavior.
        """
        self.source.commit()
        self._pending_commit = False

    def _commit_if_pending(self) -> None:
        """
        Commit offsets if a batch was stored by the background thread.

        WHY THIS EXISTS:
        The background timeout monitor thread can flush and store batches, but it
        cannot safely call Kafka commit() while the main thread is in consumer.poll().
        Instead, it sets _pending_commit=True. The main thread calls this method
        to commit when it next runs (after receiving a record or at shutdown).

        If we crash after storage but before this commit, records will be re-read
        and re-processed on restart - preserving at-least-once semantics.
        """
        if self._pending_commit:
            self._commit_source_offsets()

    def run(self):
        """
        Runs the batching projector.

        Reads records from the source, batches them, and passes batches to the storage function.
        """
        self.display_startup_banner()
        self.print_coloured(
            f"Waiting for data from {self.source} - will batch and write to {self.target_store}"
        )
        self.print_coloured(
            f"Batch size: {self.batch_size}, Timeout: {self.batch_timeout_secs}s, "
            f"Retries: {self.storage_retry_count}"
        )

        if self.reporter is not None:
            self.reporter.run()
            self.print_coloured(
                f"Telicent Live Reporter registered to send heartbeats to {self.reporter.sink}"
            )

        with self.source:
            try:
                self.started()
                self.__print_source_status__(self.source)
                self._disable_source_auto_commit()
                self._start_timeout_monitor()

                for _, record in enumerate(self.source.data()):
                    # Commit any pending offsets from background thread flushes.
                    # Must be done on main thread for Kafka consumer thread safety.
                    self._commit_if_pending()

                    # Extract traceparent for distributed tracing
                    try:
                        traceparent = list(
                            RecordUtils.get_headers(record, "traceparent")
                        )[-1]
                    except IndexError:
                        traceparent = None

                    carrier = {"traceparent": traceparent}
                    ctx = TraceContextTextMapPropagator().extract(carrier)

                    with self.tracer.start_as_current_span(
                        "process record", context=ctx
                    ) as tracer_span:
                        self.record_read()

                        # Extract request ID for tracing
                        try:
                            input_request_id = list(
                                RecordUtils.get_headers(record, "Request-Id")
                            )[-1]
                        except IndexError:
                            pass
                        else:
                            tracer_span.set_attribute(
                                "record.input_request_id", input_request_id
                            )

                        # Add to batch
                        with self._lock:
                            if self._batch_start_time is None:
                                self._batch_start_time = time.monotonic()
                            self._batch.append(record)

                        # Check if we should flush
                        if self._should_flush_batch():
                            self._flush_batch()

                # Stop the timeout monitor and flush any remaining records
                self._stop_timeout_monitor()
                self._flush_batch()
                self._commit_if_pending()

                self.finished()

            except KeyboardInterrupt:
                # Stop monitor and flush remaining on interrupt
                self._stop_timeout_monitor()
                self._flush_batch()
                self._commit_if_pending()
                self.__print_source_status__(self.source)
                self.update_status(Status.TERMINATED)
                self.aborted()

            except Exception as e:
                self._stop_timeout_monitor()
                print()
                self.send_exception(e)
                self.__print_source_status__(self.source)
                self.update_status(Status.ERRORING)
                self.print_coloured(
                    "ERROR: Unexpected error during processing, is your storage function faulty?"
                )
                self.aborted()
                raise
