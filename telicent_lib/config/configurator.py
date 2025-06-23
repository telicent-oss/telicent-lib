import logging
import sys
from collections.abc import Callable
from enum import Enum
from typing import Any

from telicent_lib.config.configSource import ConfigSource, EnvironmentSource

__license__ = """
Copyright (c) Telicent Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

logger = logging.getLogger(__name__)


class OnError(Enum):
    """
    Possible on error behaviours.

    There is `RAISE_EXCEPTION` to raise en exception and `EXIT` to exit the program.
    """

    RAISE_EXCEPTION = 1,
    EXIT = 2


class Configurator:
    """
    A configurator is a helper for reading in configuration backed by an arbitrary configuration source.

    See the `get()` method for the main utility.
    """

    def __init__(self, config_source: ConfigSource = None, exit_code: int = 1, debug: bool = False):
        """
        Creates a new configurator backed by the provided configuration source.

        :param config_source: Configuration Source from where raw configuration values may be read
        :param exit_code: Exit Code to use when retrieving configuration with an `on_error` behaviour of `EXIT`
        :param debug: Debugs configuration retrieval
        """
        if config_source is None:
            config_source = EnvironmentSource()
        if not isinstance(config_source, ConfigSource):
            raise TypeError('Not provided with a valid ConfigSource')

        self.exit_code = exit_code
        self.debug = debug
        self.source = config_source
        if self.debug:
            logger.debug(f"Configuration Source is {str(self.source)}")

    @staticmethod
    def string_to_bool(value):
        if value.lower() == 'true':
            return True
        elif value.lower() == 'false':
            return False
        else:
            raise ValueError("raw value must be 'true' or 'false'")

    def get(self, config_key: str, default: Any = None, required: bool = False, description: str = None,
            converter: Callable[[str], Any] = None, required_type: type = None,
            on_error: OnError = OnError.EXIT) -> Any:
        """
        Gets the value for a given configuration key or produces an error.

        This function can optionally convert the value from a string into a typed value and/or enforce a required type
        on the value.

        The error behaviour is configured via the `on_error` parameter.  Raising an exception or exiting the program
        are the two supported behaviours.

        :param config_key: Configuration Key
        :param required:
            Whether this configuration is considered as Required.  If `True` the configuration is considered required
            and its value cannot evaluate to `None`.  If `False` (the default) then the configuration is optional.  If
            required configuration is not present, and no `default` parameter is provided an error is produced.
        :param description:
            Description for the configuration that may be included in some error messages.
        :param converter:
            Converter function to convert from the string value provided by the Configuration Source into a typed value.
            If no function is supplied values are returned exactly as returned by the Configuration Source i.e. as
            strings.  If the converter function raises an exception during conversion then an error is produced.
        :param required_type:
            If specified requires that the configuration value after application of the `converter` function is an
            instance of the given type otherwise an error is produced.
        :param default:
            Default value, used if the configuration key's value, as provided by the Configuration Source, is `None`.
        :param on_error:
            Controls behaviour when an error is detected e.g. a required configuration key has no value and no suitable
            default value.
        :return: Configuration value
        :raises ValueError:
            Raised if a suitable configuration value is not provided and `on_error` was `OnError.RAISE_EXCEPTION`
        """
        value: Any = None
        raw_value = self.source.get(config_key)
        if self.debug:
            logger.debug(f"Raw Value for Configuration Key {config_key} is {raw_value}")

        if raw_value is None:
            raw_value = default
            if self.debug and default is not None:
                logger.debug(f"Using default value {default}")
            if raw_value is None and required:
                self.__handle_errors__(f"Required Configuration Key {config_key} is not set.  {description}", on_error)

        if converter is not None:
            try:
                value = converter(raw_value)
                if self.debug:
                    logger.debug(f"Converted raw value {raw_value} into typed value {value} with type {type(value)}")
            except Exception as e:
                self.__handle_errors__(
                    f"Configuration Key {config_key} has raw value {raw_value} that failed value conversion: {e}",
                    on_error)
        else:
            value = raw_value

        if required_type is not None:
            if not isinstance(value, required_type):
                self.__handle_errors__(
                    f"Configuration Key {config_key} has typed value {value} of type {type(value)}"
                    "which is not of the desired type {required_type}",
                    on_error)

        return value

    def __handle_errors__(self, message: str, on_error: OnError):
        """
        Handles configuration errors

        :param message: Error message
        :param on_error: On Error behaviour
        """
        if on_error is OnError.EXIT:
            logger.critical(message)
            sys.exit(self.exit_code)
        else:
            raise ValueError(message)
