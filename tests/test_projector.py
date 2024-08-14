from __future__ import annotations

import unittest

from telicent_lib import Projector, Record, RecordProjector
from telicent_lib.sources.listSource import ListSource
from tests.test_records import RecordVerifier


def __noop_projector__(record: Record) -> None:
    pass


def __fail_projector__(record: Record) -> None:
    raise ValueError("Can't project this record")


def __args_projector__(record: Record, **kwargs) -> None:
    print(kwargs["test"])


class CollectingProjector(RecordProjector):
    def __init__(self):
        self.data: list[Record] = []

    def __call__(self, record: Record) -> None:
        self.data.append(record)

    def get(self) -> list[Record]:
        return self.data


class TestProjector(RecordVerifier):

    def test_bad_projector_01(self):
        with self.assertRaisesRegex(TypeError, expected_regex=".*required positional argument.*projector_function.*"):
            Projector(source=ListSource(), target_store="Test", has_reporter=False, has_error_handler=False)

    def test_bad_projector_02(self):
        with self.assertRaisesRegex(ValueError, expected_regex=".*cannot be None"):
            Projector(source=ListSource(), target_store="Test", projector_function=None,
                      has_reporter=False, has_error_handler=False)

    def test_projector_01(self):
        source = ListSource(self.__generate_records__(10))
        projector = Projector(source=source, target_store="Test", projector_function=__noop_projector__,
                              has_reporter=False, has_error_handler=False)
        projector.run()

    def test_projector_02(self):
        source = ListSource(self.__generate_records__(10))
        projector = Projector(source=source, target_store="Test", projector_function=__noop_projector__,
                              text_colour=None, has_reporter=False, has_error_handler=False)
        projector.run()

    def test_projector_03(self):
        source = ListSource(self.__generate_records__(10))
        projector = Projector(source=source, target_store="Test", projector_function=__fail_projector__,
                              has_reporter=False, has_error_handler=False)
        with self.assertRaisesRegex(ValueError, expected_regex="Can't project this record"):
            projector.run()

    def test_projector_04(self):
        source = ListSource(self.__generate_records__(10))
        collector = CollectingProjector()
        projector = Projector(source=source, target_store="Test", projector_function=collector,
                              has_reporter=False, has_error_handler=False)
        projector.run()

        self.assertEqual(len(collector.get()), 10)
        self.assertEqual(collector.get(), source.list)

    def test_projector_args(self):
        source = ListSource(self.__generate_records__(10))
        projector = Projector(source=source, target_store="Test", projector_function=__args_projector__,
                              test="foo", has_error_handler=False, has_reporter=False,)
        projector.run()


if __name__ == '__main__':
    unittest.main()
