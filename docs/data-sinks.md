# Data Sinks

A `DataSink` provides the means to write output records for an action. This is used by the `Adapter` and `Mapper`
actions. A `DataSink` has a single `send(key, value)` method to which outputs may be sent. If you are using the
`Mapper`, or `AutomaticAdapter`, action then this is called for you using the Record your function yields. 
When creating an `Adapter`, you will need to call this yourself.

## Kafka Sink

The `KafkaSink` will deliver your records to Kafka. It requires a topic be specified, and also allows further configuration
but will use sensible default if not.

```python
from telicent_lib.sinks import KafkaSink

sink = KafkaSink(topic="output-topic")
```

### Configuring Kafka

To configure Kafka, you may provide an additional parameter, `kafka_config`. This is a configuration dictionary
that is passed to the underlying `confluent-kafka` library. You can therefore consult 
[confluent-kafka's own documentation](https://github.com/confluentinc/librdkafka/blob/master/CONFIGURATION.md)
for a full specification of available configuration options.

The minimum configuration required for a `KafkaSink` is to specify the broker to deliver records to. This can be specified
manually by passing it as part of the `kafka_config`, or by setting the `BOOTSTRAP_SERVERS` [configuration](configuration.md) 
variable. The latter is advised to prevent repetitively specifying the broker for all sinks, including telicent-lib's 
internal sinks.

```python
from telicent_lib.sinks import KafkaSink

kafka_config = {
  'bootstrap.servers': 'localhost:1234'
}
sink = KafkaSink(topic="output-topic", kafka_config=kafka_config)
```

By default, if `BOOTSTRAP_SERVERS` is not found by the configurator, and it is not provided by kafka_config either, then
an error will be raised and your action will fail to initialise.

For more complex deployments with custom Kafka configurations, please see the [deployment notes](deployment.md).

### Controlling how Data is Serialized

Kafka stores records as `bytes` internally and when writing to Kafka we can choose how, and if, we serialize the
concrete Python types our code uses into `bytes`. By default, we assume that the keys and values are already bytes,
a `str` that can be encoded as UTF-8 bytes, or some other type that provides its own `__bytes__()` conversion.

Optionally you can provide a custom serialization function for both keys and values to control how records are
serialized via the `key_serializer` and `value_deserializer` parameters. These parameters take either a
`SerializerFunction` i.e. any Python function that can convert from any Python type into `bytes`, or a `Serializer`
instance. This function **MUST** allow for `None` values since a record may have an empty key/value. If the function
produces an error then processing it will abort further processing, so you should consider having your function produce
a `None` or another special value in this case e.g.

```python
import random
from typing import Any
from telicent_lib import Record
from telicent_lib.sinks import KafkaSink


def int_to_bytes(data: Any) -> bytes:
    if data is not None:
        try:
            return int.to_bytes(data, byteorder="big", length=4, signed=True)
        except OverflowError:
            return None
    else:
        return None


sink = KafkaSink(topic="output-topic",
                 key_serializer=int_to_bytes,
                 value_serializer=int_to_bytes)
with sink:
    for i in range(0, 10000):
        sink.send(Record(None, i, random.randint(0, 10000000), None))
```

In this example we produce 10,000 [records](records.md) with integer keys and values, using the provided `int_to_bytes`
function to serialize those into bytes. In this example no record headers or raw record type are used.

Using a function should be sufficient for most use cases, a `Serializer` will likely only be needed if serialization
requires some persistent state or configuration to be maintained. If you are using a function it must conform to the
`SerializerFunction` protocol, this requires that your function has the signature of `(data: Any) -> bytes | None`.
Attempting to use a serializer value that is not a `Serializer` instance, and does not conform to the
`SerializerFunction` protocol will result in a `TypeError`.

#### Built-In Serializer Functions

There are some built-in serializer functions provided for simple use cases, these can be imported by doing
a `from telicent_lib.sinks import Serializers` and then referring to static methods on the `Serializers` class:

- `Serializers.to_zipped_binary` - Serializes a `str` into zlib compressed UTF-8 bytes.
- `Serializers.to_binary` - Tries to serialize from any Python type into bytes. If already `bytes` leaves as-is, if a 
  `str` serializes as UTF-8 bytes, otherwise calls `bytes()` on the value and assumes the type implements 
  `__bytes__()`.  This is the default serializer function used if one is not explicitly specified.
- `Serializers.to_json` - Tries to encode any Python type into a JSON string and then serializes the resulting 
  JSON string as UTF-8 bytes.
- `Serializers.as_is` - Assumes, and enforces, that the value is already `bytes`.

Additionally, the following `Serializer` instances are provided:

- `RdfSerializer` - A serializer that serializes RDFLib `Graph`/`Dataset` objects into `bytes`.  This uses NQuads as 
  the RDF serialization with the final output being UTF-8 bytes.

Note that when using a `Serializer` instance you must pass in an instance of the class, not the class itself e.g. 
`KafkaSink(topic="example", value_serializer=RdfSerializer())`.  If you pass in the class 
itself then you will receive an error message.

## Dictionary Sink

The `DictionarySink` is intended for development and testing only, it simply collects the key and values of the output
records into a Python dictionary.

```python
from telicent_lib.sinks.dictSink import DictionarySink

sink = DictionarySink()

# Use the sink...

# Print out the dictionary
for item in sink.get().items():
    print(item)
```
