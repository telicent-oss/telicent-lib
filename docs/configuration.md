# Configuration

The `Configurator` and its associated `ConfigSource` API provides a helper for reading in configuration for your
actions.

## Reading Configuration

You create a `Configurator`, optionally providing a `ConfigSource`. If no source is provided then it defaults to
the `EnvironmentSource` which reads from the OS Environment. Once you have a `Configurator` you can call the `get()`
method to read in configuration, providing default values and converter functions as needed e.g.

```python
from telicent_lib.config import Configurator

config = Configurator()
broker = config.get("BOOTSTRAP_SERVERS", required=True,
                    description="Specifies the Kafka Bootstrap Servers to connect to.")
batch_size = config.get("BATCH_SIZE", required=False, default=100, converter=int, required_type=int)
```

In the above example we first read in configuration which we treat as a String, we make this required configuration, and
we provide a useful description of its purpose that will be output in the error message if it is missing.

Secondly we read in an optional configuration which we will be converted into an `int`, and rejected if it is not an
`int`, as this is optional a suitable default value is provided. Providing a default value for optional configuration
ensures we get a valid value back.

## Error Handling

When configuration cannot be read, or does not meet some constraints placed upon it, e.g. required configuration is
missing, fails value conversion, does not have the required type etc., then an error will be produced. How that error is
handled is controlled by the `on_error` parameter of the `get()` method. If not specified then the default value is
`OnError.EXIT` which means that your application will call `sys.exit()` to abort itself.  The error code passed to 
`sys.exit()` is controlled by the `exit_code` parameter of the `Configurator` constructor e.g.

```python
from telicent_lib.config import Configurator

config = Configurator(exit_code=127)
config.get(config_key="NO_SUCH_CONFIG", required=True)
```

Here we ask for `NO_SUCH_CONFIG` which we know does not exist and so our application would call `sys.exit(127)` and 
produce an exit code of 127.

Alternatively we can have `Configurator` just raise a `ValueError` by setting `on_error` to `OnError.
RAISE_EXCEPTION` e.g.

```python
from telicent_lib.config import Configurator, OnError

config = Configurator(exit_code=127)
config.get(config_key="NO_SUCH_CONFIG", required=True, on_error=OnError.RAISE_EXCEPTION)
```

Again we ask for `NO_SUCH_CONFIG` which we know does not exist and our application would encounter a `ValueError`.  
This error handling mode may be preferable if your application can deal with the missing configuration somehow.

## Debugging Configuration

If your application is not finding the Configuration you are expecting, and you believe it should be present you can add
the `debug` parameter to the constructor e.g.

```python
from telicent_lib.config import Configurator

config = Configurator(debug=True)
broker = config.get("BOOTSTRAP_SERVERS", required=True,
                    description="Specifies the Kafka Bootstrap Servers to connect to.")
batch_size = config.get("BATCH_SIZE", required=False, default=100, converter=int, required_type=int)
```

Which when run would produce output like the following:

```
Configuration Source is OS Environment
Raw Value for Configuration Key BOOTSTRAP_SERVERS is kafka-host:9092
Raw Value for Configuration Key BATCH_SIZE is None
Using default value 100
Converted raw value 100 into typed value 100 with type <class 'float'>
```

This allows you to see the internals of how the configuration is being read and interpreted.

## Providing a Custom ConfigSource

A `ConfigSource` provides access to raw configuration values as strings. These are used by a `Configurator` to read the
raw configuration values from the underlying configuration source. As already noted there is currently only a single
concrete implementation which is the `EnvironmentSource` that reads configuration from environment variables
via `os.getenv()`.

If you want to provide a custom configuration source this is simple enough to do since it is a very simple interface
with just a single `get()` method. You should also implement the `__str()__` method so that `Configurator` can display
the `ConfigSource` correctly when used with the [`debug`](#debugging-configuration) flag.

In the following example we provide configuration from a dictionary:

```python
from telicent_lib.config import Configurator, ConfigSource


class DictionaryConfig(ConfigSource):
    """
    A Configuration Source backed by a dictionary
    """

    def __init__(self, dictionary: dict[str, str]):
        self.configuration = dictionary

    def get(self, config_key: str):
        try:
            return self.configuration[config_key]
        except KeyError:
            return None

    def __str__(self):
        return f"Dictionary with {len(self.configuration)} items"


# Create our configurator with our custom source
config = Configurator(config_source=DictionaryConfig({"foo": "example", "batch_size": "10000"}))
```
