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


class ConfigurationException(Exception):
    """
    Raised when a components requiring a configuration doesn't receive it
    """

    def __init__(self, component, config, message="A component is missing the configuration it requires"):
        """
        :param component: component missing config
        :param config: missing config
        :param message: explanation of the error
        """
        self.component = component
        self.config = config
        self.message = message
        super().__init__(self.message)


class SourceNotFoundException(Exception):
    def __init__(self, source_name, message=None):
        self.source_name = source_name
        self.message = (message if message else f"Source {source_name} not found on the specified bootstrap" \
                         " server, are you sure this source exists?")
        super().__init__(self.message)


class DLQException(BaseException):
    """
    Raised by mappers when sending a record to a dlq
    """
