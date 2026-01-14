# telicent-lib

telicent-lib provides useful helper libraries for building Adaptors, Mappers and Projectors for the Telicent Core Platform.

## Dependencies

- Python 3.10 =\< 3.13
- Kafka*

*telicent-lib uses `confluent-kafka` to manage connections to Kafka. 
Please see [confluent-kafka's compatability documentation](https://docs.confluent.io/platform/current/installation/versions-interoperability.html) to ensure you have a compatible Kafka instance.


## Installation

```shell
pip install telicent-lib
```

## Usage

For documentation on how to use telicent-lib, please see the [documentation index](https://github.com/telicent-oss/telicent-lib/blob/main/docs/index.md).

## Class Diagram

```mermaid
classDiagram
    class Action {
        +name: str
        +tracer
        +reporter
        +run()
        +started()
        +finished()
        +aborted()
    }

    class OutputAction {
        +sink: DataSink
        +send()
    }

    class InputAction {
        +source: DataSource
        +record_read()
        +record_processed()
        +send_dlq_record()
    }

    class InputOutputAction {
        +source: DataSource
        +sink: DataSink
    }

    class Mapper {
        +map_function
        +run()
    }

    class Projector {
        +projection_function
        +target_store: str
        +run()
    }

    class BatchingProjector {
        +storage_function: BatchStorageFunction
        +target_store: str
        +batch_size: int
        +batch_timeout_secs: float
        +run()
    }

    class BaseAdapter {
        +run()
    }

    class DataSource {
        <<abstract>>
        +data() Iterable~Record~
        +remaining() int
        +close()
    }

    class DataSink {
        <<abstract>>
        +send(record)
        +close()
    }

    class KafkaSource {
        +topic: str
        +broker: str
        +set_auto_commit(enabled: bool)
        +commit()
    }

    class KafkaSink {
        +topic: str
        +broker: str
        +send(record)
    }

    class BatchStorageFunction {
        <<protocol>>
        +__call__(batch: list~BatchItem~)
    }

    class BatchItem {
        <<dataclass>>
        +key: Any
        +value: Any
        +headers: list
        +partition: int
        +offset: int
    }

    Action <|-- OutputAction
    Action <|-- InputAction
    OutputAction <|-- InputOutputAction
    OutputAction <|-- BaseAdapter
    InputOutputAction <|-- Mapper
    InputAction <|-- Projector
    InputAction <|-- BatchingProjector
    DataSource <|-- KafkaSource
    DataSink <|-- KafkaSink
    InputAction --> DataSource : source
    OutputAction --> DataSink : sink
    BatchingProjector --> KafkaSource : source
    BatchingProjector --> BatchStorageFunction : calls
    BatchStorageFunction ..> BatchItem : receives
```
