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
