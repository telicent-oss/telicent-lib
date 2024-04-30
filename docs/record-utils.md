# RecordUtils


## Manipulating Record Headers

The `RecordUtils` class provides a number of static methods for manipulating the record headers. The `headers` field of 
a `Record` tuple is a list of tuples that can be inconvenient to work with at times because the header values are 
typically stored as `bytes` internally. 

You can access the value of a header via the `RecordUtils.get_first_header(record, header)` method. This provides the
first value for the header (if any) as an `Optional[str]`. `get_frist_header` either returns `None` if no such header exists, or the
first value for the header decoded into a `str`. Note that the header key given is matched in a case-insensitive manner,
so `RecordUtils.get_first_header(record, "test")` will find the first header named `test` regardless of case, i.e.
`test`, `TEST` and `Test` would all match.  Conversely, if you are interested only in the most recently added header of
this name you can use `RecordUtils.get_last_header(record, header)` instead.

If you need all the values for a header then `RecordUtils.get_headers(record, header)` return an `Iterable` over those
values.

You can add additional headers to a `Record` via the `RecordUtils.add_header(record, header, value)` method for a single
header or `RecordUtils.add_headers(record, headers)` to add multiple headers. Adding headers creates a new copy of the
`Record` with the additional header(s) appended to the end of the existing headers.  Thus, if you use this method you
must make sure to capture and use the returned `Record` instance in further code or your changes will be lost.

You can also remove headers from a `Record` via the `RecordUtils.remove_header(record, header, value)` method. The
`value` may be `None` in which case all instance of the given header are removed, if a value is provided then only
matching headers that have the exact value given are removed. As with adding headers, removing headers creates a new
copy of the `Record` with the relevant headers removed so, again, you must capture and use the returned `Record` instance
in further code.

For creating an initial set of headers for a `Record` where you don't need multiple instances of any header it can
be more convenient to represent the headers as a Python dictionary. A `RecordUtils.to_headers(dictionary,
existing_headers)` method is provided to support.  This can take just a dictionary to create a new set of 
headers, or it can take a dictionary and a list of existing headers allowing combining new headers with existing ones.

```python
from telicent_lib import Record, RecordUtils

# Create a new Record using to_headers() to convert from dictionary to list of tuples for our headers
record = Record(RecordUtils.to_headers({"Content-Type": "application/turtle",
                                        "Exec-Path": "data-source",
                                        "Version": "1.3.7"}), "key", "value")

# Alternatively we could append our new headers to existing ones
original_record: Record = load_some_record()
record = Record(RecordUtils.to_headers({"Content-Type": "application/turtle",
                                        "Exec-Path": "data-source",
                                        "Version": "1.3.7"}, original_record.headers), original_record.key, "new-value")

# Add additional header
record = RecordUtils.add_header(record, "Exec-Path", "example-app")

# Would print "data-source" as that's the first value for this header
print("First Exec-Path Header: ", RecordUtils.get_first_header(record, "Exec-Path"))

# Would print "example-app" as that's the last value for this header
print("Last Exec-Path Header: ", RecordUtils.get_last_header(record, "Exec-Path"))

# Would print "data-source" then "example-app"
for value in RecordUtils.get_headers(record, "Exec-Path"):
    print(value)
```

[1]: https://docs.python.org/3/library/collections.html?highlight=namedtuple#collections.namedtuple
[2]: https://docs.python.org/3/library/typing.html?highlight=protocol#typing.Protocol
