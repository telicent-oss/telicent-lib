# Error Handling

telicent-lib will report any errors encountered within an Adaptor, Mapper, or Projector execution to a Kafka topic by default. 

It is possible at run-time to set headers to be included in all error messages and to access the error handler directly to provide fine-graining control over the behaviour of the application, for example, allowing execution to continue is an error is encountered with a specific record.

## Headers

Headers can either be updated or replaced entirely. 

```python
adapter.error_handler.set_headers({'Security-Label': 'NAT:TS'})
```

To replace a header entirely:

```python
adapter.error_handler.set_headers(
    {'Content-Type': 'application/json', 'Security-Label': 'NAT:TS'},
    merge=False
)
```

## Manually Reporting Errors

The error handler can be accessed directly to either send an error string or a captured exception. By handling errors manually within a loop the program can be instructed to continue to the next iteration rather than exiting completely.

```python
...
def process_data():
    with open('input.csv') as f:
        for line_no, line in enumerate(f.readlines()):
            try:
                parts = line.split(',')
                adapter.send(create_record({'key': parts[0].strip("\""), 'value': int(parts[1])}))
            except ValueError:  # Caused by int() not receiving a valid integer value
                adapter.send_error('Data contained a non-integer value', error_type='DataError', level=ErrorLevel.INFO)
                continue
            except Exception as e:
                adapter.send_exception(e)
                continue
...
```

## Dead Letter Queues

When mapping data, an invalid or failed record can be sent to a dead letter queue. If the mapper uses
a `KafkaSink`, the dead letter queue is automatically initialised using a topic with "-dlq" appended to the 
target topic. E.g. a mapper targetting "knowledge" would have a dead letter queue, "knowledge-dlq".

When mapping an item, if an error is encountered a `DLQException` can be raised. The exception
message should state the reason for the item going to DLQ.

```python
from telicent_lib.exceptions import DLQException


def my_mapper(record):
    ...
    if not valid_function(data):
       raise DLQException("Record did not pass validation function") 
    ... 
```

This will create a message in the dead letter queue topic on Kafka with the initial input record as the message's
body. Additionally, the exception message will be present in a `Dead-Letter-Reason` header and the offset of the record
will be present in the `Dead-Letter-Offset` header.


### Manually managing a Dead Letter Queue with a mapper

It is possible to manually configure and manage a dead letter queue. This is required when using
a mapper with a target that is not a `KafkaSink`.

You must initialise your own sink and provide that to the mapper. The sink does not have to be 
of the same class as the mapper's target sink, but it must extend the `DataSink` base class.

```python
my_dlq = MySink()
mapper.set_dlq_target(my_dlq)
```

### Sending messages to a dead letter queue from an adapter

Unlike with a mapper, an adapter has no inbound Kafka record. The inbound record will depend
on the source being adapted. It is still possible to make use of a dead letter queue, it just 
requires the user manages the data that is sent to it.

```python
adapter.send_dlq_record(record, dlq_reason, dlq_offset)
```


## Configuration

### Environment Variables

The default error handler can be configured and even replaced through environmental variables.

ERROR_HANDLER_CLASS
    : *default*: telicent_lib.error.KafkaErrorHandler.

ERROR_HANDLER_PROVENANCE_TOPIC
    : *default*: provenance.errors


### Code Configuration

```python
# Replace with different error handler
from telicent_lib.errors import FileBasedErrorHandler

error_handler = FileBasedErrorHandler(component_id='my-adapter', file_path='errors.log')
adapter = Adapter(target=target, name=name, source_name=source_name, error_handler=error_handler)

# Disable the error handler
adapter = Adapter(target=target, name=name, source_name=source_name, has_error_handler=False)
```
