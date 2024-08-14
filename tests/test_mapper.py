from __future__ import annotations

import unittest
from unittest.mock import patch

from telicent_lib import Mapper, Record, RecordMapper
from telicent_lib.sinks.listSink import ListSink
from telicent_lib.sources.listSource import ListSource
from tests.delaySink import DelaySink
from tests.test_records import RecordVerifier


def __cube_keys__(record: Record) -> Record | list[Record] | None:
    if record is None:
        return None
    if isinstance(record.key, str):
        raise ValueError(record.key)
    return Record(record.headers, record.key * record.key * record.key, record.value, record.raw)


def __power_keys__(record: Record, **map_args) -> Record | list[Record] | None:
    if record is None:
        return None
    return Record(record.headers, record.key ** map_args["power"], record.value, record.raw)


def __fail_mapping__(record: Record) -> Record | list[Record] | None:
    raise ValueError("Can't map this record")


class SideChannelMapper(RecordMapper):
    def __init__(self):
        self.data: list[Record] = []

    def __call__(self, record: Record) -> Record | list[Record] | None:
        self.data.append(record)
        return __cube_keys__(record)

    def get(self):
        return self.data


class TestMapper(RecordVerifier):

    def setUp(self) -> None:
        super().setUp()
        self.default_headers = [
            ('Request-Id', b'List:uuid4'),
            ('Exec-Path', b'Mapper-from-In-Memory List(10 records)-to-In-Memory List'),
            ('traceparent', b'')
        ]

    def __verify_cubed_keys__(self, sink: ListSink, total: int, power: int = 3, headers=None):
        self.assertEqual(len(sink.get()), total)
        for i in range(0, total):
            actual = sink.get()[i]
            expected_key = i + 1
            expected_value = str(expected_key)
            expected_key = expected_key ** power
            self.__validate_record__(actual, key=expected_key, value=expected_value, headers=headers)

    def test_bad_mapper_01(self):
        with self.assertRaisesRegex(TypeError, expected_regex=".*required positional argument.*map_function.*"):
            Mapper(source=ListSource(), target=ListSink(), has_reporter=False, has_error_handler=False)

    def test_bad_mapper_02(self):
        with self.assertRaisesRegex(ValueError, expected_regex=".*cannot be None"):
            Mapper(source=ListSource(), target=ListSink(), map_function=None, has_reporter=False,
                   has_error_handler=False)

    def test_bad_mapper_03(self):
        with self.assertRaisesRegex(TypeError, expected_regex=".*for protocol.*RecordMapper.*"):
            Mapper(source=ListSource(), target=ListSink(), map_function=self.__verify_cubed_keys__, has_reporter=False,
                   has_error_handler=False)

    @patch('telicent_lib.adapter.uuid.uuid4')
    def test_mapper_01(self, patched_method):
        patched_method.return_value = 'uuid4'
        source = ListSource(self.__generate_records__(10))
        sink = ListSink()
        mapper = Mapper(source=source, target=sink, map_function=__cube_keys__, has_reporter=False,
                        has_error_handler=False)
        mapper.run()

        self.__verify_cubed_keys__(sink, 10, headers=self.default_headers)

    @patch('telicent_lib.adapter.uuid.uuid4')
    def test_mapper_02(self, patched_method):
        patched_method.return_value = 'uuid4'
        source = ListSource(self.__generate_records__(10))
        sink = ListSink()
        mapper = Mapper(source=source, target=sink, map_function=__cube_keys__, text_colour=None, has_reporter=False,
                        has_error_handler=False)
        mapper.run()

        self.__verify_cubed_keys__(sink, 10, headers=self.default_headers)

    def test_mapper_03(self):
        source = ListSource(self.__generate_records__(10))
        sink = ListSink()
        mapper = Mapper(source=source, target=sink, map_function=__fail_mapping__, has_reporter=False,
                        has_error_handler=False)
        with self.assertRaisesRegex(ValueError, expected_regex="Can't map this record"):
            mapper.run()

        # Mapping function errors so will produce no outputs
        self.assertEqual(len(sink.get()), 0)

    @patch('telicent_lib.adapter.uuid.uuid4')
    def test_mapper_04(self, patched_method):
        patched_method.return_value = 'uuid4'
        source = ListSource(self.__generate_records__(10))
        sink = ListSink()
        map_func = SideChannelMapper()
        mapper = Mapper(source=source, target=sink, map_function=map_func, has_reporter=False, has_error_handler=False)
        mapper.run()

        self.__verify_cubed_keys__(sink, 10, headers=self.default_headers)
        self.assertEqual(len(map_func.get()), 10)
        self.assertEqual(map_func.get(), source.list)

    @patch('telicent_lib.adapter.uuid.uuid4')
    def test_mapper_05(self, patched_method):
        patched_method.return_value = 'uuid4'
        source = ListSource(self.__generate_records__(10))
        # Ensure that when the sending of messages is happening on a background thread that the sink is closed and those
        # messages are sent
        sink = DelaySink()
        mapper = Mapper(source=source, target=sink, map_function=__cube_keys__, text_colour=None, has_reporter=False,
                        has_error_handler=False)
        mapper.run()

        self.__verify_cubed_keys__(sink, 10, headers=self.default_headers)

    @patch('telicent_lib.adapter.uuid.uuid4')
    def test_mapper_06(self, patched_method):
        patched_method.return_value = 'uuid4'
        records = self.__generate_records__(9)
        records.append(Record(headers=None, key="Error", value=None))
        source = ListSource(records)
        # Ensure that when the sending of messages is happening on a background thread that the sink is closed and those
        # messages are sent, especially if an error occurs!
        sink = DelaySink()
        mapper = Mapper(source=source, target=sink, map_function=__cube_keys__, text_colour=None, has_reporter=False,
                        has_error_handler=False)
        with self.assertRaisesRegex(ValueError, expected_regex="Error"):
            mapper.run()

        self.__verify_cubed_keys__(sink, 9, headers=self.default_headers)

    @patch('telicent_lib.adapter.uuid.uuid4')
    def test_mapper_extra_args_01(self, patched_method):
        patched_method.return_value = 'uuid4'
        source = ListSource(self.__generate_records__(10))
        sink = ListSink()
        mapper = Mapper(source=source, target=sink, map_function=__power_keys__, power=3, has_reporter=False,
                        has_error_handler=False)
        mapper.run()
        self.__verify_cubed_keys__(sink, 10, headers=self.default_headers)

        sink = ListSink()
        mapper = Mapper(source=source, target=sink, map_function=__power_keys__, power=5, has_reporter=False,
                        has_error_handler=False)
        mapper.run()
        self.__verify_cubed_keys__(sink, 10, 5, headers=self.default_headers)


if __name__ == '__main__':
    unittest.main()
