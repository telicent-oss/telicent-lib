from __future__ import annotations

import configparser
import logging
from abc import ABC, abstractmethod

from telicent_lib.config import Configurator, OnError

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


class KafkaConfig(ABC):

    def __init__(self):
        self.conf = Configurator()

    @abstractmethod
    def get_config(self) -> dict:
        pass


class BasicKafkaConfig(KafkaConfig):
    """
    A basic, default Kafka configuration intended to get up and running with a local broker.

    It is not possible to customise this configuration with authentication, or any other bespoke configuration.
    """

    def get_config(self) -> dict:
        logger.warning('Basic kafka config has been selected. This is intended for development purposes only.')
        return {
            'bootstrap.servers': self.conf.get('BOOTSTRAP_SERVERS', required=True, on_error=OnError.RAISE_EXCEPTION),
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False,
        }


class TomlKafkaConfig(KafkaConfig):
    """
    Class capable of loading a toml-like file for kafka config. It's toml-like because it's based around Java
    properties files which are very much toml-like, if not explicitly toml.

    A valid file path must be set with telicent-lib's only configurator with the key KAFKA_CONFIG_FILE_PATH
    pointing to the configuration file's absolute path.
    """

    def get_config(self) -> dict:
        config_file_path = self.conf.get('KAFKA_CONFIG_FILE_PATH', required=True, on_error=OnError.RAISE_EXCEPTION)
        logger.debug(f'loading kafka config from: {config_file_path}')
        parser = configparser.ConfigParser()
        with open(config_file_path) as stream:
            # prepend a section header. Note: toml parser would be better, but we need to support pre-3.11
            parser.read_string("[kafka]\n" + stream.read())
            conf = {}
            for (key, value) in parser['kafka'].items():
                conf[key] = value
        return conf


class KafkaConfigFactory:
    """
    Factory to ensure the correct Kafka config is supplied in each environment.

    The factory can be passed a valid `conf_method`, or determine it from the configurator key `KAFKA_CONFIG_MODE`
    """

    def __init__(self):
        self._auth_methods: dict[str, type[KafkaConfig]] = {}
        self.conf = Configurator()

    def register_conf_method(self, conf_method: str, auth_class: type[KafkaConfig]):
        self._auth_methods[conf_method] = auth_class

    def create(self, conf_method: str | None = None) -> KafkaConfig:
        if conf_method is None:
            conf_method = self.conf.get('KAFKA_CONFIG_MODE', 'basic').lower()
        conf_class = self._auth_methods.get(conf_method)
        if not conf_class:
            raise ValueError(
                f'{conf_method} is not a valid auth mode. Valid options: {", ".join(self._auth_methods.keys())}'
            )
        return conf_class()


kafka_config_factory = KafkaConfigFactory()
kafka_config_factory.register_conf_method('basic', BasicKafkaConfig)
kafka_config_factory.register_conf_method('toml', TomlKafkaConfig)
