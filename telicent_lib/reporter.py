from __future__ import annotations

import json
import logging
import sys
import threading
import time
import uuid
from datetime import datetime
from signal import SIGINT, SIGTERM, signal
from threading import Thread

import pytz

from telicent_lib.config import Configurator
from telicent_lib.records import Record
from telicent_lib.sinks.dataSink import DataSink
from telicent_lib.sinks.kafkaSink import KafkaSink
from telicent_lib.status import Status

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


class Reporter:
    """
    A reporter is an internal actions that reports to Telicent CORE the status of the component.

    A reporters main responsibility is to register components to the CORE and provide a heartbeat for reporting.
    """
    def __init__(self, action_name: str = None, target_name: str = None, target_type: str = None,
                 source_name: str = None, source_type: str = None, action: str = None, heartbeat_time: float = 15.0,
                 action_id: str = None, sink: DataSink | None = None):

        config = Configurator()

        if sink is None:
            heart_beat_provenance_topic = config.get("HEART_BEAT_PROVENANCE_TOPIC", "provenance.live")
            sink = KafkaSink(topic=heart_beat_provenance_topic)

        self.counter: int = 0
        self.total_timer: float = 0.0
        self.batch_timer: float = 0.0
        self.instance_id = uuid.uuid4()
        self.sink = sink
        self.destination = target_name
        self.target_type = target_type
        self.source = source_name
        self.source_type = source_type
        self.action_name = action_name
        self.id = action_id
        self.type = action
        self.created = str(datetime.now())
        self.status = Status.STARTED
        self.task_cancelled = False
        self.thread = None
        self.heartbeat_time = heartbeat_time
        self.heartbeat_wait = threading.Event()
        self.register()

    def get_details(self):
        return {
            "id": self.id,
            "instance_id": str(self.instance_id),
            "name": self.action_name,
            "timestamp": datetime.now(pytz.utc).isoformat(),
            "component_type": self.type,
            "reporting_period": self.heartbeat_time,
            "input": {"name": self.source, "type": self.source_type},
            "output": {"name": self.destination, "type": self.target_type},
            "status": self.status.name,
        }

    def register(self):
        self.status = Status.STARTED
        self.sink.send(
            Record(None, None, json.dumps(self.get_details()), None))

    def __terminate__(self, *args):
        self.status = Status.TERMINATED
        self.stop_heartbeat(*args)

    def __unregister__(self, *args):
        self.task_cancelled = True
        self.heartbeat_wait.set()
        self.updated = str(datetime.now())
        self.send_heartbeat()
        self.thread.join()

        # Ensure we close the sink so any outstanding status reports are sent
        self.sink.close()

        if args:
            print(args)
            sys.exit(0)

    def run(self):
        self.started()
        self.thread = Thread(target=self.start_heartbeat, args=())
        self.thread.start()
        signal(SIGTERM, self.__terminate__)
        signal(SIGINT, self.__terminate__)

    def set_status(self, status: Status):
        self.status = status

    def stop_heartbeat(self, *args):
        self.task_cancelled = True
        self.heartbeat_wait.set()
        self.__unregister__(*args)
        self.finished()

    def start_heartbeat(self):
        self.status = Status.RUNNING
        while not self.task_cancelled:
            self.send_heartbeat()

            # Use a Threading Event to sleep, this allows the main thread to immediately interrupt us by calling set()
            # on this event.  This avoids a potential hang for up to heartbeat_time seconds that was previously observed
            # with calling sleep() directly
            self.heartbeat_wait.wait(self.heartbeat_time)

    def send_heartbeat(self):
        self.sink.send(Record(None, None, json.dumps(self.get_heartbeat()), None))

    def get_heartbeat(self):
        details = self.get_details()
        return details

    def __reset_counters__(self) -> None:
        """
        Resets the internal progress counters and timers
        """
        self.counter = 0
        self.total_timer = 0.0
        self.batch_timer = 0.0

    def started(self) -> None:
        self.total_timer = time.perf_counter()
        self.batch_timer = self.total_timer
        self.counter = 0

    def finished(self) -> None:
        self.__reset_counters__()
