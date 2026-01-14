from collections.abc import Iterable
from unittest import TestCase

from telicent_lib import Record, RecordUtils
from telicent_lib.batching_projector import (
    BatchingProjector,
    BatchItem,
)
from telicent_lib.sinks.listSink import ListSink
from telicent_lib.sources.kafkaSource import KafkaSource


class MockKafkaSource(KafkaSource):
    """Mock KafkaSource for testing that doesn't require a real Kafka connection."""

    def __init__(self, records: list[Record]):
        # Skip KafkaSource.__init__ to avoid Kafka connection
        self._records = records
        self._index = -1
        self._auto_commit_enabled = True
        self._commits = 0

    def data(self) -> Iterable[Record]:
        return self

    def __iter__(self):
        self._index = -1
        return self

    def __next__(self):
        self._index += 1
        if self._index >= len(self._records):
            raise StopIteration
        return self._records[self._index]

    def close(self) -> None:
        self._index = -1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_source_name(self):
        return "MockKafka"

    def remaining(self) -> int | None:
        return None

    def set_auto_commit(self, enabled: bool) -> None:
        self._auto_commit_enabled = enabled

    def commit(self) -> None:
        self._commits += 1

    def __str__(self):
        return f"MockKafkaSource({len(self._records)} records)"


class TestBatchItem(TestCase):
    def test_batch_item_creation(self):
        item = BatchItem(
            key="test-key",
            value={"data": "test"},
            headers=[("header1", b"value1")],
            partition=0,
            offset=100,
            topic="test-topic",
            timestamp=1234567890,
            raw=None,
        )
        self.assertEqual(item.key, "test-key")
        self.assertEqual(item.value, {"data": "test"})
        self.assertEqual(item.partition, 0)
        self.assertEqual(item.offset, 100)
        self.assertEqual(item.topic, "test-topic")
        self.assertEqual(item.timestamp, 1234567890)


class TestBatchingProjector(TestCase):
    def _create_record(self, key: str = "key", value: str = "value") -> Record:
        headers = {"Some-Header": "some-value"}
        return Record(
            headers=RecordUtils.to_headers(headers), key=key, value=value, raw=None
        )

    def test_batches_by_size(self):
        stored_batches: list[list[BatchItem]] = []

        def storage_func(batch: list[BatchItem]) -> None:
            stored_batches.append(batch)

        records = [self._create_record(f"key{i}", f"value{i}") for i in range(5)]
        source = MockKafkaSource(records)

        projector = BatchingProjector(
            storage_function=storage_func,
            target_store="test-store",
            source=source,
            batch_size=2,
            batch_timeout_secs=60.0,
            has_reporter=False,
            has_error_handler=False,
        )
        projector.run()

        # 5 records with batch size 2 = 3 batches (2, 2, 1)
        self.assertEqual(len(stored_batches), 3)
        self.assertEqual(len(stored_batches[0]), 2)
        self.assertEqual(len(stored_batches[1]), 2)
        self.assertEqual(len(stored_batches[2]), 1)

    def test_batch_items_contain_record_data(self):
        stored_batches: list[list[BatchItem]] = []

        def storage_func(batch: list[BatchItem]) -> None:
            stored_batches.append(batch)

        records = [
            self._create_record("key1", "value1"),
            self._create_record("key2", "value2"),
        ]
        source = MockKafkaSource(records)

        projector = BatchingProjector(
            storage_function=storage_func,
            target_store="test-store",
            source=source,
            batch_size=10,
            has_reporter=False,
            has_error_handler=False,
        )
        projector.run()

        self.assertEqual(len(stored_batches), 1)
        self.assertEqual(len(stored_batches[0]), 2)

        # Check first item
        item1 = stored_batches[0][0]
        self.assertEqual(item1.key, "key1")
        self.assertEqual(item1.value, "value1")
        self.assertIsNotNone(item1.headers)

        # Check second item
        item2 = stored_batches[0][1]
        self.assertEqual(item2.key, "key2")
        self.assertEqual(item2.value, "value2")

    def test_storage_retry_on_failure(self):
        call_count = 0

        def storage_func_fails_twice(batch: list[BatchItem]) -> None:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Storage failed")

        records = [self._create_record()]
        source = MockKafkaSource(records)

        projector = BatchingProjector(
            storage_function=storage_func_fails_twice,
            target_store="test-store",
            source=source,
            batch_size=10,
            storage_retry_count=3,
            has_reporter=False,
            has_error_handler=False,
        )
        projector.run()

        # Should have retried 3 times and succeeded on 3rd
        self.assertEqual(call_count, 3)

    def test_storage_failure_splits_batch_and_dlqs_failures(self):
        stored_items: list[BatchItem] = []

        def storage_func_fails_on_batch(batch: list[BatchItem]) -> None:
            if len(batch) > 1:
                raise Exception("Batch storage failed")
            # Single items succeed except key2
            if batch[0].key == "key2":
                raise Exception("Item storage failed")
            stored_items.extend(batch)

        records = [
            self._create_record("key1"),
            self._create_record("key2"),
            self._create_record("key3"),
        ]
        source = MockKafkaSource(records)
        dlq_sink = ListSink()

        projector = BatchingProjector(
            storage_function=storage_func_fails_on_batch,
            target_store="test-store",
            source=source,
            batch_size=10,
            storage_retry_count=2,
            has_reporter=False,
            has_error_handler=False,
        )
        projector.set_dlq_target(dlq_sink)
        projector.run()

        # key1 and key3 should be stored
        self.assertEqual(len(stored_items), 2)
        stored_keys = [item.key for item in stored_items]
        self.assertIn("key1", stored_keys)
        self.assertIn("key3", stored_keys)

        # key2 should be in DLQ
        self.assertEqual(len(dlq_sink.get()), 1)
        self.assertEqual(dlq_sink.get()[0].key, "key2")

    def test_empty_source(self):
        stored_batches: list[list[BatchItem]] = []

        def storage_func(batch: list[BatchItem]) -> None:
            stored_batches.append(batch)

        source = MockKafkaSource([])

        projector = BatchingProjector(
            storage_function=storage_func,
            target_store="test-store",
            source=source,
            batch_size=10,
            has_reporter=False,
            has_error_handler=False,
        )
        projector.run()

        self.assertEqual(len(stored_batches), 0)

    def test_storage_function_receives_args(self):
        received_args: dict = {}

        def storage_func(batch: list[BatchItem], custom_arg: str = None) -> None:
            received_args["custom_arg"] = custom_arg

        records = [self._create_record()]
        source = MockKafkaSource(records)

        projector = BatchingProjector(
            storage_function=storage_func,
            target_store="test-store",
            source=source,
            batch_size=10,
            has_reporter=False,
            has_error_handler=False,
            custom_arg="test-value",
        )
        projector.run()

        self.assertEqual(received_args["custom_arg"], "test-value")

    def test_headers_are_preserved(self):
        stored_batches: list[list[BatchItem]] = []

        def storage_func(batch: list[BatchItem]) -> None:
            stored_batches.append(batch)

        headers = {"Custom-Header": "custom-value", "Another-Header": "another-value"}
        record = Record(
            headers=RecordUtils.to_headers(headers), key="key", value="value", raw=None
        )
        source = MockKafkaSource([record])

        projector = BatchingProjector(
            storage_function=storage_func,
            target_store="test-store",
            source=source,
            batch_size=10,
            has_reporter=False,
            has_error_handler=False,
        )
        projector.run()

        self.assertEqual(len(stored_batches), 1)
        item = stored_batches[0][0]
        self.assertIsNotNone(item.headers)
        # Headers are preserved as list of tuples
        self.assertEqual(len(item.headers), 2)

    def test_headers_dict_property(self):
        item = BatchItem(
            key="test-key",
            value="test-value",
            headers=[("Header-One", b"value1"), ("Header-Two", b"value2")],
            partition=0,
            offset=100,
            topic="test-topic",
            timestamp=1234567890,
            raw=None,
        )

        headers_dict = item.headers_dict
        self.assertEqual(headers_dict["Header-One"], "value1")
        self.assertEqual(headers_dict["Header-Two"], "value2")

    def test_headers_dict_with_none_headers(self):
        item = BatchItem(
            key="test-key",
            value="test-value",
            headers=None,
            partition=0,
            offset=100,
            topic="test-topic",
            timestamp=1234567890,
            raw=None,
        )

        self.assertEqual(item.headers_dict, {})

    def test_headers_dict_duplicate_keys_last_wins(self):
        item = BatchItem(
            key="test-key",
            value="test-value",
            headers=[("Key", b"first"), ("Key", b"second"), ("Key", b"third")],
            partition=0,
            offset=100,
            topic="test-topic",
            timestamp=1234567890,
            raw=None,
        )

        self.assertEqual(item.headers_dict["Key"], "third")

    def test_timeout_flushes_partial_batch(self):
        """Test that a partial batch is flushed after timeout even with no new records."""
        stored_batches: list[list[BatchItem]] = []
        flush_times: list[float] = []
        import time

        def storage_func(batch: list[BatchItem]) -> None:
            flush_times.append(time.monotonic())
            stored_batches.append(batch)

        # Only 2 records, batch size is 10, so won't flush by size
        records = [
            self._create_record("key1", "value1"),
            self._create_record("key2", "value2"),
        ]
        source = MockKafkaSource(records)

        projector = BatchingProjector(
            storage_function=storage_func,
            target_store="test-store",
            source=source,
            batch_size=10,  # Won't be reached
            batch_timeout_secs=0.5,  # Short timeout for test
            has_reporter=False,
            has_error_handler=False,
        )
        projector.run()

        # Should have flushed once with both records
        self.assertEqual(len(stored_batches), 1)
        self.assertEqual(len(stored_batches[0]), 2)

    def test_commits_after_successful_batch_storage(self):
        """Test that offsets are committed after each successful batch storage."""
        stored_batches: list[list[BatchItem]] = []

        def storage_func(batch: list[BatchItem]) -> None:
            stored_batches.append(batch)

        records = [self._create_record(f"key{i}", f"value{i}") for i in range(5)]
        source = MockKafkaSource(records)

        projector = BatchingProjector(
            storage_function=storage_func,
            target_store="test-store",
            source=source,
            batch_size=2,
            batch_timeout_secs=60.0,
            has_reporter=False,
            has_error_handler=False,
        )
        projector.run()

        # 5 records with batch size 2 = 3 batches
        self.assertEqual(len(stored_batches), 3)
        # Should have committed 3 times (once per batch)
        self.assertEqual(source._commits, 3)
        # Auto-commit should have been disabled
        self.assertFalse(source._auto_commit_enabled)
