from __future__ import annotations

import inspect
import logging
import warnings

# noinspection PyProtectedMem
from confluent_kafka import Producer
from confluent_kafka.serialization import Serializer

from telicent_lib.config.kafka import kafka_config_factory
from telicent_lib.records import Record
from telicent_lib.sinks.dataSink import DataSink
from telicent_lib.sinks.serializers import SerializerFunction, Serializers
from telicent_lib.utils import check_kafka_broker_available, validate_callable_protocol

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


def __validate_kafka_serializer__(instance, name):
    """
    Validates whether something is a valid serializer function/class

    :param instance: Instance
    :param name: Name of the serializer being checked
    :raises TypeError: Raised if the given instance is not a valid serializer
    :raises ValueError: Raised if the given instance is None
    """

    # If it's an instance/subclass of the Kafka Serializer class then no further checking needed since Serializer is a
    # Python metaclass so any subclass of it must implement the required interface
    if not isinstance(instance, Serializer):
        # Could be a subclass of our defined SerializerFunction protocol in which case validate it immediately
        # Note, the Serializer class of confluent-kafka also matches the signature of our SerializerFunction so
        # must also confirm it is not a subclass of that.
        if inspect.isclass(instance) and \
                issubclass(instance, SerializerFunction) and not issubclass(instance, Serializer):
            validate_callable_protocol(instance, SerializerFunction)

        elif inspect.ismethod(instance) or inspect.isfunction(instance):
            # Is a method or function so validate it conforms to our required protocol
            validate_callable_protocol(instance, SerializerFunction)

        elif inspect.isclass(instance):
            raise TypeError(
                f"Provided {name} is not a function/method/Serializer instance but was the class {instance},"
                "perhaps you meant to pass in an instance of this class instead?")

        else:
            raise TypeError(f"Provided {name} is not a function/method/Serializer instance")


class KafkaSink(DataSink):
    """A Data Sink backed by Apache Kafka"""

    def __init__(self, topic: str, broker: str | list[str] | None = None, kafka_config: dict | None = None,
                 debug: bool = False, key_serializer: SerializerFunction | Serializer = Serializers.to_binary,
                 value_serializer: SerializerFunction | Serializer = Serializers.to_binary):
        """
        Creates a new Kafka Data Sink that writes records to the specified topic

        Kafka stores records as bytes so the keys and values must be serialized into bytes.  You can optionally supply
        serializer functions that will perform this conversion for you.  This means that actual actions need not
        directly serialize their outputs and instead rely on the sink to do that for them.

        If you don't supply these functions explicitly then a default deserializer function is used that leaves data
        that is already bytes as-is, encodes `str` data as a UTF-8 byte sequence, and otherwise relies on the data being
        of a type that implements the `__bytes__()` function to provide its own `bytes` conversion.  The serializers may
        either be a Python function, or an instance of kafka-python's :class:`kafka.Serializer` class.

        :param topic: Kafka topic to send data to
        :type topic: str
        :param broker: Deprecated, please specify broker through kafka_config
        :type broker: str
        :param kafka_config: Kafka configuration
        :type kafka_config: dict
        :param key_serializer: A serialization function/class used to serialize the record keys to bytes
        :type key_serializer: SerializerFunction | Serializer
        :param value_serializer: A serialization function/class used to serialize the record values to bytes
        :type value_serializer: SerializerFunction | Serializer
        """
        if broker is not None:
            warnings.warn(
                "Parameter 'broker' has been deprecated. Please provide 'kafka_config'.",
                DeprecationWarning,
                stacklevel=2
            )
        if debug:
            warnings.warn(
                "Parameter 'debug' has been deprecated. Please use a logger to view debug messages.",
                DeprecationWarning,
                stacklevel=2
            )
        super().__init__(topic)

        __validate_kafka_serializer__(key_serializer, "key_serializer")
        __validate_kafka_serializer__(value_serializer, "value_serializer")

        if kafka_config is None:
            kafka_config = kafka_config_factory.create().get_config()

        # There are likely to be some config options specifically for consumers that will raise warnings.
        # These can be sensibly predicted and mitigated.
        consumer_specific_config = ['auto.offset.reset', 'enable.auto.commit']
        for exp_config in consumer_specific_config:
            if exp_config in kafka_config:
                del kafka_config[exp_config]

        self.broker = broker
        self.topic = topic
        self.debug = debug

        logging.debug(f"Configured KafkaSink to connect to {self}")

        check_kafka_broker_available(kafka_config)
        self.target = Producer(kafka_config)

        self.key_serializer = key_serializer
        self.value_serializer = value_serializer

    def send(self, record: Record = None):
        if record is None:
            return

        # Kafka expects the record headers to consist of tuples of (str, bytes)
        # Callers might have created tuples of (str, str) for their convenience which we can easily convert into the
        # appropriate format.
        # Note that this is not an in-depth check of the headers since KafkaProducer will do a more detailed validation
        # of them when we try to send the record
        if record.headers is not None:
            if isinstance(record.headers, list):
                for i, header in enumerate(record.headers):
                    key, value = header
                    if not isinstance(value, bytes):
                        if isinstance(value, str):
                            record.headers[i] = (key, value.encode("utf-8"))
                        else:
                            raise TypeError("Record headers must be tuples where the value is given as bytes or a str")

        key = self.key_serializer(record.key)
        value = self.value_serializer(record.value)

        while True:
            try:
                self.target.produce(self.topic,
                                    key=key,
                                    value=value,
                                    headers=record.headers)
                self.target.poll(0)
                break
            except BufferError:
                logger.debug('Waiting for buffer to clear')
                self.target.poll(1)

    def close(self):
        self.target.flush()

    def __str__(self):
        return f"Kafka {self.broker}::{self.topic}"
