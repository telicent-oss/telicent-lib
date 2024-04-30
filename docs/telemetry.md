# OpenTelemetry

telicent-lib provides metrics and traces that can be collected through OpenTelemetry.

Users can collect the data using automatic instrumentation, or in more complex use-cases, through specifying 
manual instrumentation.

For more information about implementing OpenTelemetry instrumentation in applications see 
[OpenTelemetry in Python](https://opentelemetry.io/docs/instrumentation/python/).


## Metrics

| Metric                          | Type | Description                  |
|---------------------------------|------|------------------------------|
 | \<action\>.items.processed_rate | Gauge | Records processed per second |
 | \<action\>.items.output_rate    | Gauge | Records output per second    |
 | \<action\>.items.read           | Counter | Total records read           |
 | \<action\>.items.procesed       | Counter | Total records processed      |
 | \<action\>.items.output         | Counter | Total records output         |
 | \<action\>.items.error_total         | Counter | Total errors encountered     |

### Counts for Adapters and Projectors

telicent-lib will automatically count read, processed, and output records, but there are some situations where the decision 
made by an action cannot be captured automatically by telicent-lib.

* telicent-lib cannot automatically count when an adapter has read a record or processed a record that it then discards. 
* telicent-lib cannot automatically determine if a projector output a record or not.

A user must therefore tell telicent-lib when one of these events occur.
```python
def adapter_function() -> Record:
 
    for record in record_set:
        adapter.record_read()  # called each time a record is read from the source
        ...
        if save_record:
            yield record
        else:
            adapter.record_processed()  # called only when a record is discarded
```

```python
def projector_function(record: Record) -> None:
    ...
    projector.record_output()  # called only if the record was output
```


## Tracing

Tracing of records through multiple actions is achieved by telicent-lib automatically injecting a `traceparent` 
string in to the headers of each message written to Kafka.

The next action to read the record then continues the trace and injects its own unique id ready for the next action to continue.  

This allows tools such as Jaeger to create architecture and trace visualisations through multiple components.

Users can also insert spans in to their own functions, e.g. in to a mapping function, to trace their own paths by 
accessing the tracer included with each action type.

```python
def mapping_functions(records: Record) -> Record:
    ...
    with mapper.tracer.start_as_current_span("get URL"):
        requests.get('some url')
    ...
```

Additional attributes are included with traces that can be searched in many visualisation tools.

| Attribute         | Description                  |
|-------------------|------------------------------|
| record.request_id | The record's ID |
| record.input_request_id | The ID of the inbound record |
| record.exec_path | The action's name |
