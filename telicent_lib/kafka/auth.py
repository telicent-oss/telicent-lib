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


def get_auth_mode() -> type[KafkaAuth]:
    auth_modes = {
        'plain': PlainKafkaAuth,
        'ssl': SSLKafkaAuth,
    }
    config = Configurator()
    kafka_auth_mode = config.get('KAFKA_AUTH_MODE', 'plain').lower()
    if kafka_auth_mode not in auth_modes:
        raise Exception(
            f'{kafka_auth_mode} is not a valid auth mode. Valid options: {", ".join(auth_modes.keys())}'
        )
    return auth_modes['kafka_auth_mode']
