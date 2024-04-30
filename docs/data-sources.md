# Data Sources

A `DataSource` provides the means to read input records for an action. This is used by the [`Mapper`](mappers.md) and
[`Projector`](projectors.md) actions. A `DataSource` is an interface with a `data()` method which provides an `Iterable` over 
the data records, which are represented as [`Record`](records.md) named tuples. Consumers of this API may call 
`enumerate(source.data())` to easily iterate over a data source. If you are using the `Mapper` or
`Projector` then this all happens automatically for you.

It also has a `close()` method that should be called when you are done with a data source, again automatic actions will
call this for you.

The `remaining()` method can be used to ask how many records remain in a data source, this returns either `None` if this
is currently unknown, or an `int` with the number of remaining records. Note that the return value of this method will
naturally change over time as the data source is consumed by an action, and if the data source is itself continuing to
receive new data.

Additionally, a `DataSource` provides `__enter__` and `__exit__` methods meaning it can be used in a `with` block to
ensure that `close()` is called. This is actually what automatic actions do internally.

For example, you might use a source as follows:

```python
from telicent_lib.sources import KafkaSource

with KafkaSource(topic="input-topic") as source:
    for i, record in enumerate(source.data):
        if i % 10000 == 0:
            print(f"Source {source} has {source.remaining():,} records remaining")
        print(f"{record.key}: {record.value}")
```

Bear in mind that typically a `DataSource` is not used directly but is consumed by an action instead.

## Kafka Source

```python
from telicent_lib.sources import KafkaSource

source = KafkaSource(topic="input-topic")
```

Note that an instance of a `KafkaSource` is stateful and **MUST** only be used by a single action i.e. if you are
creating multiple actions then each **MUST** be provided with a separate instance of this class. When used with a manual
action you **MUST** ensure that you call `close()` when you are done with the source.

### Configuring Kafka

To configure Kafka, you may provide an additional parameter, `kafka_config`. This is a configuration dictionary
that is passed to the underlying `confluent-kafka` library. You can therefore consult 
[confluent-kafka's own documentation](https://github.com/confluentinc/librdkafka/blob/master/CONFIGURATION.md)
for a full specification of available configuration options.

The minimum configuration required for a `KafkaSource` is to specify the broker to deliver records to. This can be specified
manually by passing it as part of the `kafka_config`, or by setting the `BOOTSTRAP_SERVERS` [configuration](configuration.md) 
variable. The latter is advised to prevent repetitively specifying the broker for all sinks and sources.

```python
from telicent_lib.sources import KafkaSource

kafka_config = {
  'bootstrap.servers': 'localhost:1234'
}
sink = KafkaSource(topic="output-topic", kafka_config=kafka_config)
```

If `BOOTSTRAP_SERVERS` is not found by the configurator, and it is not provided by kafka_config either, then
an error will be raised and your action will fail to initialise.

`KafkaSource` also sets a number of sensible defaults on the consumer. These can be overridden with `kafka_config`, but 
will default to the following:

auto.offset.reset
: 'earliest'

group.id
: Generated based on the module name of the action. If you have multiple actions reading from the same topic it is important that you specify a unique group.id for each.  

enable.auto.commit
: False. It is strongly recommended you leave this set to False and allow your action to handle offset commits for performance reasons, and to ensure records do not get skipped if the output of an action fails.

See [controlling what data is read](#controlling-what-data-is-read) for further information about `auto.offset.reset` and `group.id`. 

### Controlling how Data is Deserialized

Kafka stores records as `bytes` internally and when reading from Kafka we can choose how, and if, we deserialize
those `bytes` into concrete Python types. By default, we assume the record key and value are both uncompressed UTF-8
bytes representing a `str` value, and we deserialize as such.

You can optionally provide custom deserializer functions for both the keys and values via the `key_deserializer` and
`value_deserializer` parameters, since the keys and values may be of different types. These parameters both take either
a `DeserializerFunction` i.e. a Python function that can convert from `Optional[bytes]` to any Python type, or a
`Deserializer` instance. This function **MUST** allow for a `None` value, since a record may contain an empty key/value.
If the function produces an error it will abort further processing so consider returning `None` or another special value
in this case and handling those values in your code e.g.

```python
from typing import Any, Optional
from telicent_lib.sources import KafkaSource


def int_from_bytes(data: Optional[bytes]) -> Any:
    if data is None:
        return "<none>"
    try:
        if len(data) != 4:
            return "<too-long>"
        return int.from_bytes(data, byteorder="big", signed=True)
    except TypeError:
        return "<not-an-integer>"


source = KafkaSource(topic="input-topic",
                     key_deserializer=int_from_bytes)

with source:
    for i, record in enumerate(source):
        if not isinstance(record.key, int):
            print("Invalid key")
            continue

        if record.key % 2:
            print(f"Key {record.key} is even")
        else:
            print(f"Key {record.key} is odd")
```

In this example we provide the `int_from_bytes` method as the key deserializer, this will convert the record keys into
Python `int` values wherever possible. As noted our function handles the cases of a missing/invalid key so that our
processing can continue regardless of bad records.

Using a function should be sufficient for most use cases, a `Deserializer` will likely only be needed if deserialization
requires some persistent state or configuration to be maintained. If you are using a function it must conform to the
`DeserializerFunction` protocol, this requires that your function has the signature of `(data: bytes) -> Any`.
Attempting to use a deserializer value that is not a `Deserializer` instance, and does not conform to the
`DeserializerFunction` protocol will result in a `TypeError`.

#### Built-In Deserializer Functions

There are some built-in deserializer functions provided for simple use cases, these can be imported by doing
a `from telicent_lib.sources import Deserializers` and referring to one of the static methods:

- `Deserializers.unzip_to_string` - Deserializes from zlib compressed UTF-8 bytes into a `str`
- `Deserializers.binary_to_string` - Deserializes from UTF-8 bytes into a `str`. This is the default deserializer
  function used if not explicitly specified.
- `Deserializers.from_json` - Deserializes from UTF-8 bytes that are encoding a JSON string into a Python object.  
  The type of the returned object will depend on the JSON string.

Additionally, the following `Deserializer` instances are available:

- `RdfDeserializer` - Deserializes from UTF-8 bytes that are encoding RDF using NQuads serialization into a RDFLib
  `Dataset` object.

Note that when using a `Deserializer` instance you must pass in an instance of the class, not the class itself e.g.
`KafkaSource(topic="example", value_deserializer=RdfDeerializer())`. If you pass in the class
itself then you will receive an error message.

### Controlling what Data is Read

#### Consumer Groups

The default behaviour of a `KafkaSource`, if no explicit read behaviour related parameters are provided, is to read the
entirety of the configured topic in an exactly-once manner. This means that every record in a topic is read once, and
only once.

This is achieved my making use of Kafka's Consumer Group subscription feature. For each consumer group Kafka tracks the
offsets for each topic partition, thus in the event of any failure it can resume reading the topic from the last known
position. The Consumer Group may be specified by settings the `group.id` of the `kafka_config` dictionary.
If it is not specified then a default value is automatically selected based upon the name of the calling script file. 
For example if you had a script `my_awesome_action.py` that creates a `KafkaSource` the default `group.id` value 
would be `my_awesome_action`.

Each action **MUST** be provided with a **unique** consumer group otherwise actions will use other actions read
positions and potentially miss reading some records. Therefore, it is **strongly** recommended that you set the
`group.id` parameter explicitly, especially if your script uses multiple `KafkaSource` instances.

```python
from telicent_lib.sources import KafkaSource

kafka_config = {
  'group.id': 'my-app',
}
source = KafkaSource(topic="input-topic", kafka_config=kafka_config)
```

#### Offset Reset 

The starting position for reads can optionally be modified via the `auto.offset.reset` key of the `kafka_config` dictionary. 
For valid values, please consult [confluent-kafka's own documentation](https://github.com/confluentinc/librdkafka/blob/master/CONFIGURATION.md).

The behaviour of some commonly used values is described below.

##### `earliest`

`earliest` is the default behaviour, if the read position is not known for a given consumer group it starts from the
earliest available offsets in the topic. This means that each consumer group reads the entire topic exactly once.

##### `latest`

`latest` is useful if you want to run only on new records i.e. you don't care about old records. If the read position is
not known for a given consumer group it starts from the latest available offsets in the topic.  **BUT**
if the consumer group has a known position then it resumes from there.

So in practise this reset mode basically acts as read only records from the first point in time this consumer group was
used e.g.

```python
from telicent_lib.sources import KafkaSource

kafka_config = {
  'group.id': 'latest-app',
  'auto.offset.reset': 'latest'
}
source = KafkaSource(topic="input-topic", kafka_config=kafka_config)
```

##### `beginning`

`beginning` is needed if you want to re-process a topic that has previously been read. It resets the read position to
the earliest available offsets in each topic. This effectively forces a full re-processing of all records present in the
topic e.g.

```python
from telicent_lib.sources import KafkaSource

kafka_config = {
  'group.id': 'beginning-app',
  'auto.offset.reset': 'beginning'
}
source = KafkaSource(topic="input-topic", kafka_config=kafka_config)
```

Would cause all records in `input-topic` to be read, regardless of whether they have previously been read.

##### `end`

`end` is useful for demonstration and testing where you only want to process new records. It resets the read position to
the latest available offsets in each topic. This means that it will only read records that are created after the
application was started e.g.

```python
from telicent_lib.sources import KafkaSource

kafka_config = {
  'group.id': 'end-app',
  'auto.offset.reset': 'end'
}
source = KafkaSource(topic="input-topic", kafka_config=kafka_config)
```

Would only read new records from `input-topic`.

##### Known Issues and Limitations

Since both `beginning` and `end` actively reset the read position, if you later change your application to use
`earliest` or `latest` instead, reading will still resume from the previously known read position. To avoid this you can
use a different `group.id` for testing/demo versus production, that way read positions stored during testing/demo
do not impact production.

There is currently no supported way to seek to a specific offset. This may be added in future versions of the library.

## Dictionary Source

The `DictionarySource` is intended for development and testing only. It is created by providing a dictionary with the
desired key value pairs in it, these will be converted into `Record` tuples when the source is iterated over:

```python
from telicent_lib.sources.dictSource import DictionarySource

source = DictionarySource(dict([(0, "ant"), (1, "aardvark"), (2, "bat"), (3, "camel")]))

with source:
    for i, record in enumerate(source.data()):
        print(f"{record.key}: {record.value}")

```

