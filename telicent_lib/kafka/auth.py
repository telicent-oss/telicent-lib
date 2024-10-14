from __future__ import annotations

from abc import ABC, abstractmethod

from telicent_lib.config import Configurator


class KafkaAuth(ABC):

    def __init__(self):
        self.conf = Configurator()

    @abstractmethod
    def get_config(self) -> dict:
        pass


class PlainKafkaAuth(KafkaAuth):

    def get_config(self) -> dict:
        return {}


class SSLKafkaAuth(KafkaAuth):

    def get_config(self) -> dict:
        broker = self.conf.get('BOOTSTRAP_SERVERS', required=True)
        ssl_ca_location = self.conf.get('SSL_CA_LOCATION', required=True)
        ssl_certificate_location = self.conf.get('SSL_CERTIFICATE_LOCATION', required=True)
        ssl_key_location = self.conf.get('SSL_KEY_LOCATION', required=True)
        ssl_key_password = self.conf.get('SSL_KEY_PASSWORD', required=True)
        ssl_endpoint_identification_algorithm = self.conf.get(
            'SSL_ENDPOINT_IDENTIFICATION_ALGORITHM', required=False, default='https'
        )
        return {
            'metadata.broker.list': broker,
            'security.protocol': 'SSL',
            'ssl.ca.location': ssl_ca_location,
            'ssl.certificate.location': ssl_certificate_location,
            'ssl.key.location': ssl_key_location,
            'ssl.key.password': ssl_key_password,
            'ssl.endpoint.identification.algorithm': ssl_endpoint_identification_algorithm,
        }


class AuthConfigFactory:

    def __init__(self):
        self._auth_methods = {}
        self.conf = Configurator()

    def register_auth_method(self, auth_method: str, creator: type[KafkaAuth]):
        self._auth_methods[auth_method] = creator

    def get_auth_method(self, auth_method: str | None = None):
        if auth_method is None:
            auth_method = self.conf.get('KAFKA_AUTH_MODE', 'plain').lower()
        auth_class = self._auth_methods.get(auth_method)
        if not auth_class:
            raise ValueError(
                f'{auth_method} is not a valid auth mode. Valid options: {", ".join(self._auth_methods.keys())}'
            )
        return auth_class()


auth_config_factory = AuthConfigFactory()
auth_config_factory.register_auth_method('plain', PlainKafkaAuth)
auth_config_factory.register_auth_method('ssl', SSLKafkaAuth)
