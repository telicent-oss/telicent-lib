# Logging

telicent-lib provides a flexible handler, formatter, and Adapter that integrates with Python's standard logging features giving users a fine-grained control to log messages from their applications to core.

For users who want an efficient way to send logs from their applications to Kafka, a factory is provided to initialise a logger with defaults that can be overriden on-demand.



## Python Logging Primer

Python's standard library provides flexible logging tools that can be extended to a wide range of use cases. Most users will be familiar with sending formatted log strings to either plain-text files or STDOUT, however, telicent-lib's users will likely gain more benefit from sending log entries to a Kafka topic. This is the intention behind telicent-lib's logging extensions.

Whilst telicent-lib's logging extensions have been designed to be intuitive and provide out-of-the-box functionality, users with more advanced use-cases should familiarise themselves with Python's logging features, https://docs.python.org/3/library/logging.html.



## Handler and Formatter 


### `telicent_lib.logging.KafkaHandler`

In addition to the standard `logging.Handler` parameters, `KafkaHandler` accepts:

broker
    : *Required*, the broker instance to write logs to.

topic
    : *Default: log*, the topic to write log entries to.


### `telicent_lib.logging.JSONFormatter`

In addition to the standard `logging.Formatter` parameters, `JSONFormatter` accepts:

fmt
    : *Default: ['name', 'levelname', 'msg', 'created']*, specifies which values of a log record's dictionary to include in the message

`fmt` must be provided as a list of keys to be included from the Python log entry dict. It supports additional keys added to log entries with extra. If `CoreLoggerAdaptor` is used, `headers` and `log_type` will also be available as format keys automatically. 

It is recommended not to include `headers` in the message itself when using with the `KafkaHandler` as this handler will automatically send the headers as Kafka message headers. You may still include them though, and if you are using the `JSONFormatter` with a different handler (e.g. local debugging with Python's standard `StreamHandler`) then it might be useful to include the headers in the message.



## Core Logger Adaptor

telicent-lib provides an adaptor to apply `headers` and `log_type` to all log entries as additional parameters instead of being supplied through `extra`. 
If default values are provided to the Adaptor these will be applied to all entries, however individual log entries may also specify their own values as parameters. 


### `telicent_lib.logging.CoreLoggerAdaptor`

headers
    : *Default: {}*, specifies the default headers to apply to all log messages.

log_type
    : *Default: None*, allows a user to specify a log type for granular auditing.

header_method
    : *Default: telicent-lib.logging.MERGE*, allows a user to specify whether an individual log's headers are merged with or replace the default headers dictionary. To replace the entire headers dictionary on a per-message basis instead of merging use `telicent-lib.logging.REPLACE`.



## Core Logger Factory

Python logging is highly flexible, and whilst each of the provided classes by telicent-lib can be used and configured much like the classes provided in Python's standard logging library, telicent-lib also provides a logger factory that will configure a logger that is applicable to most use-cases of telicent-lib.
The factory provides a logger with the `KafkaHandler`, `JSONFormatter` and `CoreLoggerAdaptor` configured, but each of their parameters can be overriden on initialisation. 


### `telicent_lib.logging.CoreLoggerFactory`

broker
    : *Required*, the broker instance to write logs to

topic
    : *Default: log*, the topic to write log entries to

headers
    : *Default: {}*, specifies the default headers to apply to all log messages.

log_type
    : *Default: None*, allows a user to specify a log type for granular auditing

fmt
    : *Default: ['name', 'log_type', 'levelname', 'msg', 'created', 'headers']*, specifies which values of a log record's dictionary to include in the message

header_method
    : *Default: telicent-lib.logging.MERGE*, allows a user to specify whether an individual log's headers are merged with or replace the default headers. To replace headers instead of merging use telicent-lib.logging.REPLACE.
 


## Example Usage

The logger can be configured programmatically much like any standard Python logger:

```python
import logging

from telicent_lib.logging import KafkaHandler, JSONFormatter


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = KafkaHandler("localhost:9092")
handler.setLevel(logging.INFO)
handler.setFormatter(JSONFormatter())

logger.addHandler(handler)

logger.info('Processing file: data.csv')
logger.error({'processing_file': 'data.csv', 'error': 'Cannot find file'})
``` 

The logger factory can be customised as follows:

```python
import uuid
from telicent_lib.logging import CoreLoggerFactory


logger = CoreLoggerFactory.get_logger(
    __name__, 
    broker="localhost:9092", 
    topic='audit_log', 
    headers={'Request-Id': str(uuid.uuid4()), 'Security-Label': 'NTN:S'}, 
    log_type='AuthLog'
)
user = 'John Doe'
if user.is_valid():
    logger.info(f'User {user} logged in')
else:
    logger.info(f'User {user} is invalid', headers={'Security-Label': 'NTN:TS'}, log_type='FailedAuth')
```

For advanced usage, when an application use multiple loggers, or in development where a user may want to also see log messages sent to stdout, the logger can be configured through `logging.config.dictConfig`

```python
import logging

from logging.config import dictConfig


logging_config = {
    "version": 1,
    'disable_existing_loggers': False,
    "formatters": {
        'standard': {
            'format': "%(asctime)s {app} [%(thread)d] %(levelname)-5s %(name)s - %(message)s. [file=%(filename)s:%(lineno)d]"
        },
        'json': {
            'class': 'telicent_lib.logging.JSONFormatter'
        }
    },
    "handlers": {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'level': logging.DEBUG,
            'stream': 'ext://sys.stdout'
        },
        'core': {
            'class': 'telicent_lib.logging.KafkaHandler',
            'level': logging.INFO,
            'formatter': 'json',
            'broker': "localhost:9092"
        }
    },
    "loggers": {
        "my_module": {
            'handlers': ['core', 'console'],
            'level': logging.DEBUG
        }
    }
}

dictConfig(logging_config)
logger = logging.getLogger('my_module')

logger.info('This message will be wrapped in JSON to send to Kafka, but also be formatted as a standard log entry to the console')
logger.debug('This is debug info, so only goes to the console')
```
