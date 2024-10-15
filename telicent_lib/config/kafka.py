from __future__ import annotations

import configparser
import logging
from abc import ABC, abstractmethod

from telicent_lib.config import Configurator, OnError

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

    def __init__(self):
        self._auth_methods: dict[str, type[KafkaConfig]] = {}
        self.conf = Configurator()

    def register_auth_method(self, auth_method: str, auth_class: type[KafkaConfig]):
        self._auth_methods[auth_method] = auth_class

    def create(self, auth_method: str | None = None) -> KafkaConfig:
        if auth_method is None:
            auth_method = self.conf.get('KAFKA_CONFIG_MODE', 'basic').lower()
        auth_class = self._auth_methods.get(auth_method)
        if not auth_class:
            raise ValueError(
                f'{auth_method} is not a valid auth mode. Valid options: {", ".join(self._auth_methods.keys())}'
            )
        return auth_class()


kafka_config_factory = KafkaConfigFactory()
kafka_config_factory.register_auth_method('basic', BasicKafkaConfig)
kafka_config_factory.register_auth_method('toml', TomlKafkaConfig)
