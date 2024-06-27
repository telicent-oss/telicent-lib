# telicent-lib

## Actions

Actions provide automation and progress monitoring of data processing tasks. A component within Telicent Core will typically be implemented using one or more of the subclasses of `Action`.

[Actions](actions.md) | [Adapters](adapters.md) | [Mappers](mappers.md) | [Projectors](projectors.md)

## Record Handling

A `DataSource` provides input from a source (e.g. a Kafka consumer), whilst a `DataSink` handles the output (e.g. a Kafka producer). 
`RecordUtils` manipulates headers.

[DataSource](data-sources.md) | [DataSink](data-sinks.md) | [RecordUtils](record-utils.md)


## Utilities and Helpers

telicent-lib provides a number of features out of the box to support development, configuration, error handling and audit logging.

[Configuration](configuration.md) | [Logging](logging.md) | [Error Handling](error-handling.md) | [Provenance and Audit](provenance.md) | [Telemetry](telemetry.md) | [SecurityLabel modules](security-label-modules)
