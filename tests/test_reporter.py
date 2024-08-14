import json
import time
import unittest

from telicent_lib.reporter import Reporter
from telicent_lib.sinks.listSink import ListSink
from telicent_lib.status import Status
from tests.test_records import RecordVerifier


class TestReporter(RecordVerifier):
    # Need to break this up and add more but should do for now
    def test_reporter_01(self):
        reporter_sink = ListSink()
        reporter = Reporter(
            action_name="Test", target_name="destination", source_name="source", action="mapper", sink=reporter_sink
        )
        received = json.loads(reporter.sink.get().pop().value)
        self.assertEqual(received["name"], "Test")
        self.assertEqual(received["component_type"], "mapper")
        self.assertEqual(received["status"], "STARTED")
        self.assertEqual(received["input"]["name"], "source")
        self.assertEqual(received["output"]["name"], "destination")
        reporter.run()
        time.sleep(2)
        received = json.loads(reporter.sink.get().pop().value)
        self.assertEqual(received["name"], "Test")
        self.assertEqual(received["status"], "RUNNING")
        time.sleep(2)
        reporter.set_status(Status.COMPLETED)
        reporter.stop_heartbeat()
        received = json.loads(reporter.sink.get().pop().value)
        self.assertEqual(received["name"], "Test")
        self.assertEqual(received["status"], "COMPLETED")
        reporter.set_status(Status.ERRORING)
        reporter.send_heartbeat()
        received = json.loads(reporter.sink.get().pop().value)
        self.assertEqual(received["name"], "Test")
        self.assertEqual(received["status"], "ERRORING")

    def test_reporter_no_termination_hang(self):
        reporter_sink = ListSink()
        start = time.perf_counter()
        reporter = Reporter(action_name="Test", target_name="destination", source_name="source", action="mapper",
                            heartbeat_time=5, sink=reporter_sink)
        reporter.run()
        time.sleep(1)
        reporter.stop_heartbeat()
        elapsed = time.perf_counter() - start
        self.assertTrue(elapsed < 5, "Expected reporter to terminate immediately")


if __name__ == '__main__':
    unittest.main()
