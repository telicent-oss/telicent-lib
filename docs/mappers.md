# Mappers

A `Mapper` is an action used to transform data already within Telicent Core, depending on their purpose they may be
referred to as mappers, resolvers or cleaners.  A `Mapper` is an automatic action meaning that you only need create it
with the desired [`DataSource`](data-sources.md), [`DataSink`](data-sink.md) and mapping function, before calling
`run()` to run the mapping process for you.

## Mapping Functions

A mapping function conforms to the [`RecordMapper`](records.md#working-with-records) protocol, this means it must have
the following signature:

```python
from typing import List, Union
from telicent_lib import Record

def example_mapping_function(record: Record) -> Union[Record, List[Record], None]:
    return record
```

The function takes in an input [`Record`](records.md) and returns 0, 1 or more output records as its result.  Therefore,
a mapping function can do several things:

- Filter out records by returning `None` for input records you don't want to process
- Perform a [map() operation][1] i.e. map each input record to a single output record
- Perform a [flatMap() operation][2] where each input record produces an arbitrary number of output records

### Advanced Mapping Functions

As mapping functions must conform to the `RecordMapper` protocol, which is itself a class, you can if you wish 
subclass this class to create advanced mapping functions e.g. those that store state, hold access to some resource 
etc., by extending this class.  For example consider the following example:

```python
from typing import List, Union
from telicent_lib import Record, RecordMapper

class MyCustomMapper(RecordMapper):
  def __init__(self):
    # Create some reference to some external service your Mapper needs
    self.external_service = connect_to_service()

  def __call__(self, record: Record) -> Union[Record, List[Record], None]:
    if self.external_service.should_transform(record):
        return self.external_service.transform_record(record)
    else:
        return record
```

Here we create a mapping function encapsulated in a class, allowing us to neatly wrap accompanying resources of the 
mapping function in the instance of the class.  Note that we could have done the same just by defining a bare 
function that uses a global variable but this gives slightly nicer encapsulation.

## Example Usage

In this example we use the a [`DictionarySource`](data-sources.md#dictionary-source) and a
[`DictionarySink`](data-sinks.md#dictionary-sink) to provide dummy data for the mapper.

```python
from typing import List, Union
from telicent_lib import Record, Mapper
from telicent_lib.sinks.dictSink import DictionarySink
from telicent_lib.sources.dictSource import DictionarySource

# Define a mapping function
def to_upper(record: Record) -> Union[Record, List[Record], None]:
    if record.key == 0:
        return None
    if record.key == 1:
        return Record(record.headers, record.key, str.upper(record.value), None)

    records: List[Record] = []
    for i in range(0, record.key):
        records.append(Record(record.headers, record.key, str.upper(record.value), None))
    return records


# Create a Mapper and run it
sink = DictionarySink()
mapper = Mapper(source=DictionarySource(dict([(0, "ant"), (1, "aardvark"), (2, "bat"), (3, "camel")])),
                target=sink, map_function=to_upper)
mapper.run()

# After the mapper has completed print the records collected by the sink
for item in sink.get().items():
    print(item)
```


[1]: https://en.wikipedia.org/wiki/Map_(higher-order_function)
[2]: https://stackoverflow.com/questions/26684562/whats-the-difference-between-map-and-flatmap-methods-in-java-8
