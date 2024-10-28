from __future__ import annotations

import inspect
import logging
import warnings
from collections.abc import Iterable

from confluent_kafka import OFFSET_BEGINNING, OFFSET_END, Consumer, Message, TopicPartition
from confluent_kafka.serialization import Deserializer

from telicent_lib.config.kafka import kafka_config_factory
from telicent_lib.exceptions import SourceNotFoundException
from telicent_lib.records import Record
from telicent_lib.sources.dataSource import DataSource
from telicent_lib.sources.deserializers import DeserializerFunction, Deserializers
from telicent_lib.utils import check_kafka_broker_available, generate_group_id, validate_callable_protocol

logger = logging.getLogger(__name__)


def __validate_kafka_deserializer__(instance, name):
    """
    Validates whether something is a valid deserializer function/class

    :param instance: Instance
    :param name: Name of the deserializer being checked
    :raises TypeError: Raised if the given instance is not a valid serializer
    :raises ValueError: Raised if the given instance is None
    """

    # If it's an instance/subclass of the Kafka Serializer class then no further checking needed since Serializer is a
    # Python metaclass so any subclass of it must implement the required interface
    if not isinstance(instance, Deserializer):
        # Could be a subclass of our defined SerializerFunction protocol in which case validate it immediately
        # Note, the Deserializer class of confluent-kafka also matches the signature of our DeserializerFunction so
        # must also confirm it is not a subclass of that.
        if inspect.isclass(instance) and issubclass(instance, DeserializerFunction) and \
                not issubclass(instance, Deserializer):
            validate_callable_protocol(instance, DeserializerFunction)

        elif inspect.ismethod(instance) or inspect.isfunction(instance):
            # Is a method or function so validate it conforms to our required protocol
            validate_callable_protocol(instance, DeserializerFunction)

        elif inspect.isclass(instance):
            raise TypeError(
                f"Provided {name} is not a function/method/Deserializer instance but was the class {instance},"
                "perhaps you meant to pass in an instance of this class instead?")

        else:
            raise TypeError(f"Provided {name} is not a function/method/Deserializer instance")


class KafkaSource(DataSource):
    """
    A Data Source backed by Apache Kafka
    """

    def __init__(self, topic, broker: str | list[str] | None = None, kafka_config: dict | None = None,
                 key_deserializer: DeserializerFunction | Deserializer = Deserializers.binary_to_string,
                 value_deserializer: DeserializerFunction | Deserializer = Deserializers.binary_to_string,
                 commit_interval: int = 10000, debug: bool = None):
        """
        The portion of that topic that will be read is controlled by the various parameters passed to this constructor
        through the kafka_config dict. For all available options, see:
            https://github.com/confluentinc/librdkafka/blob/master/CONFIGURATION.md

        The default behaviour is to use Kafka's consumer group offset tracking, and defaulting to reading from the
        earliest available offsets that have not previously been consumed with a 'auto.offset.reset' of 'earliest'.
        This means that by default, any action using this source will process each event at least once.

        Each application **MUST** provide a unique consumer group.id to ensure that they read all the data in the topic.
        If no consumer group is explicitly supplied then it is selected automatically based on the script file that is
        creating the source.  Using a consumer group enables an application to be stopped and restarted at will, and to
        benefit from Kafka's auto-scaling behaviour that assigns each application within a consumer group a fair share
        of the available topic partitions.

        Records arriving from Kafka have the key and value encoded as `bytes`, you can optionally supply deserialization
        functions that convert the byte values into an alternative type.  If you don't supply these functions explicitly
        then a default deserializer function is used that tries to convert the `bytes` into a UTF-8 `str`.  The
        deserializers may either be a Python function, or an instance of kafka-python's :class:`kafka.Deserializer`
        class.

        :param topic: The Kafka topic from which data will be read
        :type topic: str
        :param broker: Deprecated, please specify broker through kafka_config
        :type broker: str
        :param kafka_config: Kafka configuration
        :type kafka_config: dict
        :param key_deserializer: The deserializer function/class to use to deserialize record keys
        :type key_deserializer: DeserializerFunction | Deserializer
        :param value_deserializer: The deserializer function/class to use to deserialize record values
        :type value_deserializer: DeserializerFunction | Deserializer
        :param commit_interval:
            How often to commit the read position to Kafka.  Defaults to 10,000 i.e. every 10,000 records read the read
            position will be committed.  Note that the read position is also committed whenever the source is closed
            **but** we cannot guarantee that we will be closed gracefully, so we commit the read position as we go.
        :param debug:
            Deprecated, please use a logger
        :type debug: bool
        """
        if debug is not None:
            warnings.warn(
                "Parameter 'debug' has been deprecated. Please use a logger to view debug messages.",
                DeprecationWarning,
                stacklevel=2
            )
        if broker is not None:
            warnings.warn(
                "Parameter 'broker' has been deprecated. Please provide 'kafka_config'.",
                DeprecationWarning,
                stacklevel=2
            )
        super().__init__(topic)
        self.topic = topic
        self.commit_interval = commit_interval
        self.records_seen: int = 0
        self.last_known_remaining: int | None = None

        __validate_kafka_deserializer__(key_deserializer, "key_deserializer")
        __validate_kafka_deserializer__(value_deserializer, "value_deserializer")

        # Confluent Kafka's key and value deserializer consumer is still experimental, so we handle
        # deserialization ourselves for now.
        self.key_deserializer = key_deserializer
        self.value_deserializer = value_deserializer

        if kafka_config is None:
            kafka_config = kafka_config_factory.create().get_config()

        check_kafka_broker_available(kafka_config)

        reset_position = kafka_config.get('auto.offset.reset')
        if reset_position is None:
            kafka_config['auto.offset.reset'] = 'earliest'

        group_id = kafka_config.get('group.id')
        if group_id is None or len(group_id) == 0:
            logger.warning("No consumer group.id was provided, attempting to set one.")
            try:
                group_id = generate_group_id()
            except Exception:
                logger.exception("Failed to automatically create group.id")

            if group_id is None or len(group_id) == 0:
                raise ValueError("No consumer group.id was provided or could be automatically selected")
            kafka_config['group.id'] = group_id
            logger.info(f"Automatically selected consumer group.id as {group_id}")

        enable_auto_commit = kafka_config.get('enable.auto.commit')
        if enable_auto_commit is None:
            kafka_config['enable.auto.commit'] = False

        self.broker = kafka_config['bootstrap.servers']
        self.reset_position = kafka_config['auto.offset.reset']
        self.needs_seek = False

        # Create the consumer
        # NB We don't pass in our topics at this time as we want to explicitly subscribe and provide our rebalance
        # methods.  If we pass the topic in here the consumer will subscribe immediately with no rebalance methods
        # and this can result in the desired read position not being properly honoured.  Instead, once we've created the
        # consumer we explicitly subscribe providing our rebalance methods that will allow us to determine when we need
        # to reset the position.
        self.consumer = Consumer(kafka_config)
        self.consumer.subscribe(
            [self.topic],
            on_assign=self.on_partitions_assigned,
            on_revoke=self.on_partitions_revoked
        )
        self.already_seeked: list[TopicPartition] = []
        self.last_offsets: dict[TopicPartition, Message] = {}

    def on_partitions_revoked(self, consumer, partitions):
        for partition in partitions:
            logger.debug(f"Revoked topic partition {partition.topic}-{partition.partition} from consumer {consumer}")
            self.__commit_read_positions__()

    def on_partitions_assigned(self, consumer, partitions):
        try:
            for partition in partitions:
                logger.debug(f"Assigned consumer {consumer} to topic partition {partition.topic}-{partition.partition}")
            self.needs_seek = partitions is not None
            logger.debug(f"Set needs_seek={self.needs_seek}")
        except Exception as e:
            logger.exception(e)

    def data(self) -> Iterable[Record]:
        return self

    def __iter__(self):
        return self

    def __next__(self):
        """
        Gets the next record from the source
        :return: Next record
        """
        # Loop until we have a new record available, a loop is necessary because we are setting a low consumer timeout
        # to avoid a potential hang. Otherwise, we could hang forever waiting to read the latest record from a topic
        # when actually the user had configured us to seek to a different position.
        while True:
            record: Message | None = None

            if not self.needs_seek:
                # If we aren't needing a seek read the next record from the consumer
                # Have to fence this read based on the needs_seek flag as otherwise when we are at the end of the
                # topic this always fails with StopIteration which sends us back to the top of the loop and skips
                # over the seeking logic that comes afterward
                record = self.consumer.poll(timeout=1.0)

            if self.needs_seek:
                # If the rebalance listener has set the needs_seek flag do the necessary seek now
                # We can't do the seek in the rebalance listener itself because that's getting called on a
                # different thread and has a nasty habit of breaking the consumer in ways that cause it to silently
                # skip records!
                # See Issue #13 in this repo and the linked upstream kafka-python issue for more detail
                #
                # Note that we do this AFTER having first read the next record because due to the multi-threading
                # going on with the KafkaConsumer we could be assigned partitions and start reading from them prior
                # to having the opportunity to seek to our desired position.  If we do seek we do a fresh read so
                # that we get the correct record, otherwise we could return an incorrect record
                logger.debug(f"Seeking based on reset_position={self.reset_position}")
                if self.reset_position == 'beginning':
                    self.__seek_to_beginning__()
                    record = self.consumer.poll(timeout=1.0)
                elif self.reset_position == 'end':
                    self.__seek_to_end__()
                    record = self.consumer.poll(timeout=1.0)
                self.needs_seek = False

            # If we were needing a seek i.e. we'd just been assigned a partition, but didn't have to explicitly seek
            # then the record will be None, and we'll loop back round again to try reading the next record
            if record is None:
                continue

            if record.error() is not None:
                if "UNKNOWN_TOPIC_OR_PART" in record.error().__str__():
                    raise SourceNotFoundException(source_name=self.get_source_name())
                else:
                    raise RuntimeError(record.error())

            self.last_offsets[TopicPartition(record.topic(), record.partition())] = record

            # As we've disabled auto commit on the consumer we periodically commit the read positions ourselves
            self.records_seen += 1
            if self.records_seen % self.commit_interval == 0:
                self.__commit_read_positions__()

            return Record(
                headers=record.headers(),
                key=self.key_deserializer(record.key()),
                value=self.value_deserializer(record.value()),
                raw=record
            )

    def remaining(self) -> int | None:
        remaining = None

        # noinspection PyBroadException
        try:
            # As we may have multiple partitions assigned to us, we need to total up the remaining records over all the
            # partitions we're assigned
            for partition in self.consumer.assignment():
                # Ask the Kafka Consumer for the highwater mark i.e. the next offset that would be assigned in this
                # partition when another record is added to the topic.  If we have not yet fetched any records from the
                # topic then this will be unknown and return None
                low, high = self.consumer.get_watermark_offsets(partition)
                if high is None:
                    continue

                # Given the highwater mark we can calculate the remaining records, usually referred to as lag in Kafka
                # terminology, by subtracting our current position in the partition from the highwater mark
                # consumer_position = logger.debug(f'position return: {self.consumer.position([partition])}')
                position = self.consumer.position([partition])[0].offset
                remaining_in_partition = high - position
                if remaining is None:
                    remaining = remaining_in_partition
                else:
                    remaining = remaining + remaining_in_partition
        except Exception as e:
            # Ignore any errors that occur while trying to calculate remaining records.  If this happens we'll either
            # return None or our previous cached value.  There's lots of reasons that we might not be able to calculate
            # this, e.g. network partition, kafka partition rebalance, consumer closed, and we don't want to throw an
            # error here and interrupt execution flow elsewhere
            logger.debug(f'Got an exception while calculating remaining: {e}')
            pass

        # Use cached value if unable to determine a fresh value.  This might happen if the consumer has been closed,
        # partitions have been revoked etc.  If a fresh value was determined cache that for later reuse.
        if remaining is None:
            remaining = self.last_known_remaining
        else:
            self.last_known_remaining = remaining
        return remaining

    def close(self):
        """
        Closes the Kafka source ensuring that the underlying Consumer is closed and our current read position(s)
        are committed to allow us to resume from this position on future runs
        """
        remaining = self.remaining()
        if remaining is not None:
            logger.debug(f"Closing source {self} which has {remaining:,} records remaining")

        self.__commit_read_positions__()
        self.consumer.close()

        logger.debug(f"Source {self} is now closed")

    def __commit_read_positions__(self):
        """Commits the most recent read positions to Kafka"""
        for partition, message in self.last_offsets.items():
            logger.debug(
                f"Committing position {message.offset() + 1} for partition {partition.topic}-{partition.partition}"
            )
            self.consumer.commit(message=message)

    def __str__(self):
        return "Kafka " + self.broker + "::" + self.topic

    def __seek_to_beginning__(self):
        """
        Seeks to the beginning of all assigned partitions
        """
        if self.consumer.assignment() is None:
            return

        for partition in self.consumer.assignment():
            # If there's a rebalance, and we've been reassigned a partition we've previously been assigned, and thus
            # previously had chance to seek to our desired partition, then don't seek again.  Otherwise, we'll be
            # reprocessing data we've already processed
            if partition in self.already_seeked:
                continue

            logger.debug(f"Seeking to beginning of partition {partition.topic}-{partition.partition}")
            partition.offset = OFFSET_BEGINNING
            self.consumer.seek(partition)
            logger.debug(
                f"Beginning offset for partition {partition.topic}-{partition.partition} is {partition.offset:,}"
            )
            self.consumer.commit(offsets=[partition])
            self.already_seeked.append(partition)

    def __seek_to_end__(self):
        """
        Seeks to the end of all assigned partitions
        """
        if self.consumer.assignment() is None:
            return

        for partition in self.consumer.assignment():
            # If there's a rebalance, and we've been reassigned a partition we've previously been assigned, and thus
            # previously had chance to seek to our desired partition, then don't seek again. Otherwise, we'll be
            # reprocessing data we've already processed
            if partition in self.already_seeked:
                continue

            logger.debug(f"Seeking to end of partition {partition.topic}-{partition.partition}")
            partition.offset = OFFSET_END
            self.consumer.seek(partition)
            logger.debug(f"End offset for partition {partition.topic}-{partition.partition} is {partition.offset:,}")
            self.consumer.commit(offsets=[partition])
            self.already_seeked.append(partition)
