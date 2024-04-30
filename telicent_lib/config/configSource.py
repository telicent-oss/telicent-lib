import os

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


class ConfigSource:
    """
    Represents a Configuration Source that provides access to raw configuration values as strings

    Intended for use in conjunction with a `Configurator` which provides mechanisms for converting the raw values into
    typed values, supplying default values etc.
    """

    def get(self, config_key: str) -> str:
        """
        Gets the string value of the given configuration key

        :param config_key: Configuration Key
        :return: String value
        """
        raise NotImplementedError


class EnvironmentSource(ConfigSource):
    """
    A Configuration Source backed by the OS Environment i.e. `os.getenv()`
    """

    def get(self, config_key: str):
        return os.getenv(config_key)

    def __str__(self):
        return "OS Environment"
