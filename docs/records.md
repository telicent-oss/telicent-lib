# Records

A `Record` represents a data record, whether for input or output. It is a simple [Python named tuple][1] with four
fields:

- `headers` - Contains any headers for the record, either `None` or a Python list of tuples where each tuple
  consists of a string for the header key and bytes for the header value.
- `key` - Contains the key for the record, either `None` or any Python object.
- `value` - Contains the value for the record, either `None` or any Python object.
- `raw` - Contains the raw record, may be used by implementations of data sources and sinks to provide access to
  their underlying record type. May be `None` or any Python object.

A record is created by simple instantiating an instance of the tuple e.g.

```python
from telicent_lib import Record

record = Record([("Content-Type", b"example")], 12345, "Some value", None)
```

In the above example we create a record that has some headers, the key `12345` and the value `Some value`.  Note that we
encoded the header value into bytes in the example.  Our APIs for [manipulating headers](#manipulating-record-headers)
work with header values as `str` but these are generally stored as `bytes` by underlying [Data Sources](data-sources.md)
and [Data Sinks](data-sinks.md).  From a user perspective you can work with `str` values for convenience and telicent-lib
takes care of converting to/from `bytes` for you.

Since `Record` is a named tuple you can use named parameters for clarity e.g.

```python
from telicent_lib import Record

record = Record(headers=None, key=789, value="Value")
```

In this example named parameters were used for clarity, and omitted the `raw` field since that is optional and defaults 
to `None`.  Record headers are permitted to be `None` but must be explicitly stated as such.

## The `raw` field

The `raw` field is primarily an internal implementation detail that end users of this library need not be concerned
with. For example the [`KafkaSource`](data-sources.md#kafka-source) uses this field of the `Record` tuple to carry its
own internal `ConsumerRecord` tuple.

As the `raw` field is typically not needed by end users it has a default of `None` meaning you can create a `Record`
without explicitly specifying this field of the tuple.

## Working with Records

Typically, you work with records when implementing a function to pass to an action, e.g. a [`Mapper`](mappers.md),
where you define your function in terms of the `Record` type. For example consider the following map function:

```python
from telicent_lib import Record


def to_upper(record: Record) -> Record | list[Record] | None:
    if record.key == 0:
        return None
    if record.key == 1:
        return Record(record.headers, record.key, str.upper(record.value), None)

    records: list[Record] = []
    for i in range(0, record.key):
        records.append(Record(record.headers, record.key, str.upper(record.value), None))
    return records
```

In this example we implement a mapping function that produces 0 or more records depending on the key.  While this is 
clearly a toy example it demonstrates the basic idea of implementing a function that conforms to one of our defined
[Protocol][2] classes (see below) that can then be passed to another class within this library.  The above example
implements the `RecordMapper` interface and would be used with a [`Mapper`](mappers.md) action.

There are several [Protocol][2] classes defined for working with records:

- `RecordAdapter` which is the protocol that adapter functions must implement.
- `RecordMapper` which is the protocol that mapping functions must implement.
- `RecordProjector` which is the protocol that projection functions must implement.

When you attempt to instantiate an action that requires a function with one of these signatures a `TypeError` is
produced if you pass a function that does not match the signature of the relevant Protocol's `__call__()` method.  The
only exception to this is that functions may take keyword arguments as their final argument, for example we could
rewrite our earlier example like so:

```python
from telicent_lib import Record


def to_upper(record: Record, **kwargs) -> Record | list[Record] | None:
    if record.key == 0:
        return None
    if record.key == 1:
        return Record(record.headers, record.key, str.upper(record.value), None)

    records: list[Record] = []
    for i in range(0, min(record.key, kwargs["max-records"])):
        records.append(Record(record.headers, record.key, str.upper(record.value), None))
    return records
```

In this revised example our record mapper function takes in keyword arguments and uses these as a way to limit the
maximum number of output records any given input record may produce.  Note that the keyword arguments are passed as one
of the parameters to your [`Action`](actions.md) constructor so will be constant throughout the life of your action,
this means they can be used for constant configuration parameters as in this example, but not for other purposes e.g.
state management.

This is probably most relevant for adapter functions where state management may be most important, see
[Adapters](adapters.md#when-should-i-use-adapter-vs-automaticadapter) for some discussion around this topic.
