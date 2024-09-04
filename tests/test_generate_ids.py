from __future__ import annotations

from collections.abc import Iterable
from unittest import TestCase

from telicent_lib import Adapter, AutomaticAdapter, Mapper, Projector, Record
from telicent_lib.action import Action, InputAction, InputOutputAction, OutputAction
from telicent_lib.sinks.listSink import ListSink
from telicent_lib.sources.listSource import ListSource


class ActionTestCase(TestCase):

    def test_action_not_implemented(self):
        action = Action(has_error_handler=False, has_reporter=False, disable_metrics=True)
        self.assertRaises(NotImplementedError, action.generate_id)


class OutActionTestCase(TestCase):

    def test_id_is_name(self):
        action = OutputAction(target=ListSink(), has_error_handler=False, has_reporter=False, disable_metrics=True)
        self.assertEqual('None-to-In-Memory List', action.generate_id())

    def test_id_is_name_adapter(self):
        action = Adapter(target=ListSink(), has_error_handler=False, has_reporter=False, disable_metrics=True,
                         has_data_catalog=False)
        self.assertEqual('Manual Adapter-to-In-Memory List', action.generate_id())

    def test_id_is_name_automatic_adapter(self):
        def my_func() -> Iterable[Record]:
            yield Record(None, None, None, None)
        action = AutomaticAdapter(
            adapter_function=my_func, target=ListSink(), has_reporter=False, has_error_handler=False,
            disable_metrics=True, has_data_catalog=False
        )
        self.assertEqual('Automatic Adapter-to-In-Memory List', action.generate_id())

    def test_named_action(self):
        def my_func() -> Iterable[Record]:
            yield Record(None, None, None, None)
        action = AutomaticAdapter(
            adapter_function=my_func, target=ListSink(), has_error_handler=False, has_reporter=False,
            name='Test Action', disable_metrics=True, has_data_catalog=False
        )
        self.assertEqual('Test-Action', action.generate_id())


class InputActionTestCase(TestCase):

    def test_id_is_name(self):
        action = InputAction(source=ListSource(), has_error_handler=False, has_reporter=False, disable_metrics=True)
        self.assertEqual(action.generate_id(), 'None-from-In-Memory List(0 records)')

    def test_id_is_name_adapter(self):
        def my_func(record: Record) -> None:
            pass
        action = Projector(source=ListSource(), has_error_handler=False, has_reporter=False,
                           projector_function=my_func, target_store='Smart Cache', disable_metrics=True)
        self.assertEqual('Projector-from-In-Memory List(0 records)', action.generate_id())

    def test_named_action(self):
        def my_func(record: Record) -> None:
            pass
        action = Projector(source=ListSource(), has_error_handler=False, has_reporter=False,
                           projector_function=my_func, target_store='Smart Cache', name='Test Action',
                           disable_metrics=True)
        self.assertEqual('Test-Action', action.generate_id())


class InputOutputActionTestCase(TestCase):

    def test_id_is_name(self):
        action = InputOutputAction(
            source=ListSource(), target=ListSink(), has_error_handler=False, has_reporter=False, disable_metrics=True
        )
        self.assertEqual('None-from-In-Memory List(0 records)-to-In-Memory List', action.generate_id())

    def test_id_is_name_adapter(self):
        def my_func(record: Record) -> Record | list[Record] | None:
            pass
        action = Mapper(
            source=ListSource(), target=ListSink(), has_error_handler=False, has_reporter=False,
            map_function=my_func, disable_metrics=True
        )
        self.assertEqual('Mapper-from-In-Memory List(0 records)-to-In-Memory List', action.generate_id())

    def test_named_action(self):
        def my_func(record: Record) -> Record | list[Record] | None:
            pass
        action = Mapper(
            source=ListSource(), target=ListSink(), has_error_handler=False, has_reporter=False, map_function=my_func,
            name='Test Action', disable_metrics=True
        )
        self.assertEqual('Test-Action', action.generate_id())
