from __future__ import annotations

from abc import ABC, abstractmethod

from telicent_lib.config import Configurator, OnError


class KafkaConfig(ABC):

    def __init__(self):
        self.conf = Configurator()

    @abstractmethod
    def get_config(self) -> dict:
        pass


class PlainKafkaConfig(KafkaConfig):
    """
    This class provides the generic base configuration for an action.
    """

    def get_config(self) -> dict:
        return {
            'bootstrap.servers': self.conf.get('BOOTSTRAP_SERVERS', required=True, on_error=OnError.RAISE_EXCEPTION)
        }


class FileKafkaConfig(KafkaConfig):

    def get_config(self) -> dict:
        config_file_path = self.conf.get('KAFKA_CONFIG_FILE_PATH', required=True, on_error=OnError.RAISE_EXCEPTION)
        with open(config_file_path):
            ...
        return {}


class KafkaConfigFactory:

    def __init__(self):
        self._auth_methods: dict[str, type[KafkaConfig]] = {}
        self.conf = Configurator()

    def register_auth_method(self, auth_method: str, auth_class: type[KafkaConfig]):
        self._auth_methods[auth_method] = auth_class

    def create(self, auth_method: str | None = None) -> KafkaConfig:
        if auth_method is None:
            auth_method = self.conf.get('KAFKA_CONFIG_MODE', 'plain').lower()
        auth_class = self._auth_methods.get(auth_method)
        if not auth_class:
            raise ValueError(
                f'{auth_method} is not a valid auth mode. Valid options: {", ".join(self._auth_methods.keys())}'
            )
        return auth_class()


kafka_config_factory = KafkaConfigFactory()
kafka_config_factory.register_auth_method('plain', PlainKafkaConfig)
kafka_config_factory.register_auth_method('file', FileKafkaConfig)
