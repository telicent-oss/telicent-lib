# Batching Projector

A `BatchingProjector` is an action used to batch records from a data source before projecting them to an external
storage system. Unlike a standard [`Projector`](projectors.md) which processes records individually, a
`BatchingProjector` accumulates records into batches and passes them to a storage function in groups. This is
particularly useful when writing to external systems that benefit from bulk operations, such as databases or
search indices.

## Storage Functions

A storage function conforms to the `BatchStorageFunction` protocol, which means it must have the following signature:

```python
from telicent_lib import BatchItem

def example_storage_function(batch: list[BatchItem]) -> None:
    pass
```

The function receives a list of `BatchItem` objects and is responsible for persisting them to the target system.
The function should raise an exception if storage fails; the `BatchingProjector` will handle retries and error
recovery automatically.

## BatchItem

Each item in a batch is represented by a `BatchItem` dataclass with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `key` | `Any` | The record key |
| `value` | `Any` | The record value |
| `headers` | `list[tuple[str, Any]] \| None` | Raw headers as a list of tuples |
| `partition` | `int \| None` | Kafka partition (if available) |
| `offset` | `int \| None` | Kafka offset (if available) |
| `topic` | `str \| None` | Kafka topic (if available) |
| `timestamp` | `int \| None` | Record timestamp (if available) |
| `raw` | `Any` | The underlying raw record from the data source |

### Accessing Headers

`BatchItem` provides a `headers_dict` property for convenient access to headers as a dictionary:

```python
def my_storage_function(batch: list[BatchItem]) -> None:
    for item in batch:
        # Access headers as a dictionary (bytes decoded to strings)
        security_label = item.headers_dict.get("Security-Label")
        content_type = item.headers_dict.get("Content-Type")

        # Or access raw headers if needed (e.g., for multi-value headers)
        raw_headers = item.headers
```

When using `headers_dict`, byte values are automatically decoded to UTF-8 strings. If a header key appears
multiple times, the last value is returned. For multi-value header access, use the raw `headers` field directly.

## Configuration

The `BatchingProjector` supports the following configuration options, which can be set via constructor parameters
or environment variables:

| Parameter | Environment Variable | Default | Description |
|-----------|---------------------|---------|-------------|
| `batch_size` | `BATCH_SIZE` | 100 | Maximum number of records per batch |
| `batch_timeout_secs` | `BATCH_TIMEOUT_SECS` | 5.0 | Maximum time to wait before flushing an incomplete batch |
| `storage_retry_count` | `STORAGE_RETRY_COUNT` | 3 | Number of retry attempts for failed storage operations |

Constructor parameters take precedence over environment variables.

## Batch Timeout Behaviour

Batches are flushed when either condition is met:
- The batch reaches `batch_size` records, or
- The `batch_timeout_secs` timeout elapses since the first record was added to the batch

The timeout mechanism uses a background monitor thread that periodically checks whether the timeout has
elapsed. This ensures that partial batches are flushed even during quiet periods when no new records are
arriving from the source. Without this, records could remain stuck in memory indefinitely while waiting
for additional records to fill the batch.

For example, with `batch_size=100` and `batch_timeout_secs=5.0`:
- If 100 records arrive quickly, they are flushed immediately as a full batch
- If only 10 records arrive and then the stream goes quiet, those 10 records are flushed after 5 seconds

## Error Handling and Retries

When a storage function fails, the `BatchingProjector` implements the following error recovery strategy:

1. **Retry**: The batch is retried up to `storage_retry_count` times with exponential backoff.
2. **Split**: If all retries fail and the batch contains more than one item, the batch is split and each item
   is processed individually.
3. **Dead Letter Queue**: Items that fail all retry attempts are sent to the Dead Letter Queue (DLQ) if one
   has been configured via `set_dlq_target()`.

This strategy ensures that a single problematic record does not prevent the successful processing of other
records in the same batch.

### Known Behaviour: Retry Compounding

When a batch fails and is split for individual processing, each individual item receives its own set of retry
attempts. This means the total number of storage attempts for a problematic record can exceed `storage_retry_count`.

For example, with `storage_retry_count=3` and a batch containing a bad record:
- 3 attempts at the batch level (all fail)
- Batch is split into individual items
- 3 attempts for the problematic item (all fail)
- Item is sent to DLQ

The problematic record receives 6 total storage attempts (3 + 3) rather than 3. This is intentional behaviour
that maximises the chance of successful storage before resorting to the DLQ.

## Offset Commit Behaviour

`BatchingProjector` requires a `KafkaSource` and manages Kafka offset commits to prevent data loss. By default,
`KafkaSource` commits offsets as records are read. This creates a risk for batching: if records are read into
a batch but the process crashes before the batch is stored, those records would be lost.

To prevent this, `BatchingProjector` disables automatic offset commits and only commits after each batch is
successfully stored. This ensures at-least-once delivery semantics: if a crash occurs, uncommitted records
will be re-read and re-processed on restart.

When batches are flushed by the background timeout monitor thread, offset commits are deferred to the main
thread for Kafka consumer thread safety. The commit occurs when the next record is read or at shutdown. If
a crash occurs after storage but before the deferred commit, records will be re-processed on restart.

## Example Usage

### Basic Usage

```python
from telicent_lib import BatchingProjector, BatchItem
from telicent_lib.sources import KafkaSource

def store_to_database(batch: list[BatchItem]) -> None:
    # Bulk insert records into database
    records = [(item.key, item.value) for item in batch]
    database.bulk_insert(records)

source = KafkaSource(topic="input-topic", group="my-group")

projector = BatchingProjector(
    storage_function=store_to_database,
    target_store="my-database",
    source=source,
    batch_size=50,
    batch_timeout_secs=10.0,
)
projector.run()
```

### With Dead Letter Queue

```python
from telicent_lib import BatchingProjector, BatchItem
from telicent_lib.sinks import KafkaSink
from telicent_lib.sources import KafkaSource

def store_to_database(batch: list[BatchItem]) -> None:
    for item in batch:
        if not validate(item):
            raise ValueError(f"Invalid record: {item.key}")
        database.insert(item.key, item.value)

source = KafkaSource(topic="input-topic", group="my-group")
dlq_sink = KafkaSink(topic="dlq-topic")

projector = BatchingProjector(
    storage_function=store_to_database,
    target_store="my-database",
    source=source,
)
projector.set_dlq_target(dlq_sink)
projector.run()
```

### Passing Additional Arguments to Storage Function

Additional keyword arguments passed to the `BatchingProjector` constructor are forwarded to the storage function:

```python
from telicent_lib import BatchingProjector, BatchItem
from telicent_lib.sources import KafkaSource

def store_with_config(batch: list[BatchItem], index_name: str = None) -> None:
    for item in batch:
        search_engine.index(index_name, item.key, item.value)

source = KafkaSource(topic="input-topic", group="my-group")

projector = BatchingProjector(
    storage_function=store_with_config,
    target_store="search-engine",
    source=source,
    index_name="my-index",  # Passed to storage function
)
projector.run()
```

## Comparison with Projector

| Feature | Projector | BatchingProjector |
|---------|-----------|-------------------|
| Processing model | One record at a time | Batches of records |
| Retry granularity | Per record | Per batch, then per record |
| Best suited for | Simple projections, real-time processing | Bulk operations, external systems with batch APIs |
| Dead Letter Queue | Supported | Supported |
