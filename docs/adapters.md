# Adapters

An `Adapter` is an action used to import data into Telicent Core, sometimes these are referred to as Producers. With an
adapter the calling code controls an arbitrary data source, typically one that does not conform to our `DataSource` API
and calls the `send()` method to import records.  For example an adapter might be used to pull data out of a legacy 
database and write it out to a Kafka topic.

An `Adapter` is a Manual action meaning the caller has to manually call additional action methods after calling `run()`
as seen in the later example.

## Automatic Adapter

Additionally, from `0.10.0` onwards, there is an `AutomaticAdapter` provided.  This is similar to a regular `Adapter`
except that it is fully automated by providing an `adapter_function` parameter to its constructor.  This parameter
references a function that conforms to the `RecordAdapter` protocol, this function is basically a Python [generator][1]
that provides an iterable of `Record` instances.

The `AutomaticAdapter` is an automatic action since it can enumerate over the `Record` instances from the provided
adapter function and write those out to the configured data sink.

An adapter function has the following signature:

```python
from typing import Iterable
from telicent_lib import Record

def example_adapter_function() -> Iterable[Record]:
    for i in range(0, 10000):
        yield Record(headers=None, key=i, value=str(i))
```

In the above example we define a toy adapter function that generates a sequence of 10,000 records.  As already noted
this function is simply a Python [generator][1], this means it uses `yield` statements to produce the records to be
written to the `DataSink`.

## When should I use `Adapter` vs `AutomaticAdapter`?

If the records to be imported can be easily expressed as a Python generator function using an `AutomaticAdapter` should
be preferred.  This makes the action fully automated and minimises the amount of user code needed, for a practical
example contrast the two [examples](#example-usage) below.  Users of the `AutomaticAdapter` get fully automated progress
monitoring, reporting and error handling, all of which they'd have to do themselves with a manual `Adapter`.

The manual `Adapter` is preferable when producing the records requires more complex logic, and/or state management of
your data source.  Since if the action errors/aborts for any reason the state of the adapter function is effectively
thrown away with an `AutomaticAdapter`.  By using a manual `Adapter` you can provide your own error handling and state
management as needed.

Another alternative to consider is whether it would be better to implement a proper [`DataSource`](data-sources.md)
instead, as that class more naturally provides for state management of the data source.  If you choose to go down the
`DataSource` route then you would use a [`Mapper`](mappers.md) action instead of either adapter action.


## Data Catalog

An adapter can be initialised with an optional parameter, `distribution_id`. This is added to the record's headers 
automatically. See [provenance documentation](./provenance.md) for further information about automatic headers. 


## Example Usage

### Manual `Adapter`

Here's a basic example of using a manual `Adapter`, the details of how the data source is obtained and the records
transformed for ingest into Kafka are omitted:

```python
from telicent_lib import Adapter, Record
from telicent_lib.sinks import KafkaSink

# Access your data source
some_data_source = open_data_source()

# Create a sink and an adapter
sink = KafkaSink(topic="output-topic", broker="your-kafka-broker:1234")
adapter = Adapter(target=sink, name="Example Adapter", distribution_id="my-distribution-id")

try:
    # Call run() to start the action, for an adapter this just initializes progress counters
    adapter.run()

    # If you know how many records you have to import you can call expect_records()
    # This will enable percentage progress in the progress monitoring output
    adapter.expect_records(some_data_source.total_records())

    # Iterate over your data source, this example assumes your datasource implements Iterable
    # Other data sources will require other kinds of loops
    for i, record in enumerate(some_data_source):
        # Transform the record for input into the data sink
        output_record = transform_record(record)

        # Send the record to the adapter
        adapter.send(Record(None, record.id, output_record, None))

    # Call finished() when done
    adapter.finished()
except KeyboardInterrupt as e:
    # Ensure that you catch KeyboardInterrupt and inform the adapter it was aborted
    adapter.aborted()
```

Note that you have to send [`Record`](records.md) instances to the adapter. This allows for providing record
headers as well as a key and value for each record.

In this example we are not specifying how our record key and value get stored by the data sink, depending on the
data sink you may need/want to specify sink parameters to 
[control data serialization](data-sinks.md#controlling-how-data-is-serialized).

### `AutomaticAdapter`

In this example we instead use an `AutomaticAdapter` providing it a suitable adapter function that generates our
sequence of `Record` instances we want to write out to the `DataSink`:

```python
from typing import Iterable
from telicent_lib import AutomaticAdapter, Record
from telicent_lib.sinks import KafkaSink

# Access your data source
some_data_source = open_data_source()

# Define our adapter function, this is just a Python generator function that 
# generates the Record instance to be written out to the DataSink
def generate_records() -> Iterable[Record]:
    for i, record in enumerate(some_data_source):
        output_record = transform_record(record)
        yield Record(headers=None, key=i, value=output_record)

# Create a sink and the adapter
sink = KafkaSink(topic="output-topic", broker="your-kafka-broker:1234")
adapter = AutomaticAdapter(
    target=sink, adapter_function=generate_records, name="Example Adapter", distribution_id="my-data-source"
)

# Call run() to run the action
adapter.run()
```

[1]: https://docs.python.org/3/glossary.html#term-generator