# Projectors

A `Projector` is an action used to project data already within Telicent Core out into another data store, typically one
of our Smart Caches, for later consumption by applications.  A `Projector` is an automatic action meaning that you only
need create it with the desired [`DataSource`](data-sources.md) and projection function, before
calling `run()` to run the projection process for you.

## Projection Functions

A mapping function conforms to the [`RecordProjector`](records.md#working-with-records) protocol, this means it must
have the following signature:

```python
from telicent_lib import Record

def example_projection_function(record: Record) -> None:
    pass
```

The function takes in an input [`Record`](records.md) and projects it.  It has no return value meaning it has free rein
to project the record to a Smart Cache, external system or otherwise process it as it sees fits.

## Example Usage

In this example we use the a [`DictionarySource`](data-sources.md#dictionary-source) to provide dummy data, and we 
have a projection function that simply prints out the records:

```python
from telicent_lib import Projector, Record
from telicent_lib.sources.dictSource import DictionarySource

def print_records(record: Record) -> None:
    print(record)

projector = Projector(source=DictionarySource(dict([(0, "ant"), (1, "aardvark"), (2, "bat"), (3, "camel")])),
                      projector_function=print_records)
projector.run()
```

In real usage a projector function will typically process the record key and value and write some output to a Smart
Cache for later consumption by applications.


[1]: https://en.wikipedia.org/wiki/Map_(higher-order_function)
[2]: https://stackoverflow.com/questions/26684562/whats-the-difference-between-map-and-flatmap-methods-in-java-8
