
import random
import time
from typing import Any

# noinspection PyProtectedMember
from telicent_lib import Mapper, Record
from telicent_lib.action import Action
from telicent_lib.config import Configurator
from telicent_lib.sinks import KafkaSink, SerializerFunction, Serializers
from telicent_lib.sinks.dictSink import DictionarySink
from telicent_lib.sources import DeserializerFunction, Deserializers, KafkaSource
from telicent_lib.sources.dictSource import DictionarySource
from telicent_lib.utils import validate_callable_protocol


def int_to_bytes(data: Any) -> bytes | None:
    if data is not None:
        return int.to_bytes(data, byteorder="big", length=4, signed=True)
    else:
        return None


def int_from_bytes(data: bytes) -> Any:
    try:
        if len(data) != 4:
            return "<too-long>"
        return int.from_bytes(data, byteorder="big", signed=True)
    except TypeError:
        return "<not-an-integer>"


def main():
    # logging.basicConfig(level=logging.DEBUG)

    # generate_data()
    kafka_config = {
        'auto.offset.reset': 'beginning'
    }
    source = KafkaSource(
        topic="test", kafka_config=kafka_config, debug=True,  key_deserializer=int_from_bytes
    )
    with source:
        try:
            for _, msg in enumerate(source.data()):
                print(f"{msg.key}: {msg.value}")
        except KeyboardInterrupt:
            print("Interrupted")


def generate_data():
    sink = KafkaSink(topic="test", debug=True, key_serializer=int_to_bytes)
    with sink:
        try:
            for _ in range(0, 10):
                key = time.perf_counter()
                sink.send(Record(None, int(key), f"This is a test {key}", None))
                time.sleep(1)
        except KeyboardInterrupt:
            print("Interrupted")

        sink.close()


def action_test(iterations: int = 1500, with_abort: bool = True):
    action = Action(action="Projector", name="Foo")
    action.display_startup_banner()

    action.started()
    action.expect_records((iterations * 1000) + 1)
    i = 0
    try:
        while i < iterations:
            action.records_processed(random.randint(100, 1000))
            time.sleep(random.uniform(0.001, 0.05))
            i += 1

            if with_abort and random.randint(0, 1000) > 999:
                action.aborted()
                exit(1)

        action.finished()
    except KeyboardInterrupt:
        action.aborted()


def to_upper(record: Record) -> Record | list[Record] | None:
    if record.key == 0:
        return None
    if record.key == 1:
        return Record(record.headers, record.key, str.upper(record.value), None)

    records: list[Record] = []
    for _ in range(0, record.key):
        records.append(Record(record.headers, record.key, str.upper(record.value), None))
    return records


def mapper_test():
    sink = DictionarySink()
    mapper = Mapper(source=DictionarySource({0: "ant", 1: "aardvark", 2: "bat", 3: "camel"}),
                    target=sink, map_function=to_upper, name="Uppercase Transformer")
    mapper.run()

    for item in sink.get().items():
        print(item)


def not_a_deserializer(a: int, b: int) -> int:
    return a + b


def nearly_a_deserializer(data: int) -> int:
    return data


def bad_deserializer():
    KafkaSource(topic="test", key_deserializer=not_a_deserializer)


def is_a_deserializer(function: Any):
    try:
        validate_callable_protocol(function, DeserializerFunction)
        print(f"{function} is a Valid Deserializer")
    except Exception as e:
        print(e)


def is_a_serializer(function: Any):
    try:
        validate_callable_protocol(function, SerializerFunction)
        print(f"{function} is a Valid Serializer")
    except Exception as e:
        print(e)


def validate_protocols():
    is_a_deserializer(not_a_deserializer)
    is_a_deserializer(nearly_a_deserializer)
    is_a_deserializer(int_from_bytes)
    is_a_deserializer(Deserializers.binary_to_string)
    print()

    is_a_serializer(int_from_bytes)
    is_a_serializer(int_to_bytes)
    is_a_serializer(Serializers.to_binary)
    print()


def seek_hang_bug():
    # generate_data()
    kafka_config = {
        'auto.offset.reset': 'beginning',
        'group.id': 'consumer_group',
    }
    source = KafkaSource(topic="test", kafka_config=kafka_config, debug=True,
                         key_deserializer=int_from_bytes)
    try:
        with source:
            for _, record in enumerate(source):
                print(f"{record.key}: {record.value}")
    except KeyboardInterrupt:
        print("Interrupted")


def configurator_test():
    config = Configurator(debug=True, exit_code=127)
    path = config.get("PATH", required=True, description="Executable search path")
    foo = config.get("FOO", default=1.23, converter=float, required_type=float)
    print(f"PATH={path}")
    print(f"FOO={foo}")
    bar = config.get("BAR", description="Sets the bar.")
    print(f"BAR={bar}")


if __name__ == "__main__":
    seek_hang_bug()
