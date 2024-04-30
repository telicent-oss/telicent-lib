import threading
from typing import List

from telicent_lib import Record
from telicent_lib.sinks.listSink import ListSink


class DelaySink(ListSink):
    """
    A sink that simulates delayed sending of records for testing purposes.

    This is basically a simplified version of what is happening behind the scenes of a KafkaSink.  The underlying
    KafkaProducer batches up records to be sent and sends them to Kafka in batched requests using a background thread.
    This means that calling send() on the KafkaSink does not mean that Record is immediately sent, and if the
    application exited on exhaustion of its data source it could exit before all records were actually sent onwards to
    Kafka.

    However, calling close() on the KafkaProducer does ensure that any outstanding messages are sent.  Again we simulate
    this with this implementation.

    See various unit test cases that utilise this sink implementation to see the different scenarios we are testing to
    ensure that a sink is closed when an action finishes/aborts.
    """

    def __init__(self, delay_time: float = 0.1):
        super().__init__()
        self.closed = False
        self.delay = threading.Event()
        self.delay_time = delay_time
        self.delayed: List[Record] = []

        # Start a background thread that sends the records onwards after enforcing a delay on them
        self.thread = threading.Thread(target=self.__send_delayed__, args=())
        self.thread.start()

    def send(self, record: Record) -> None:
        self.delayed.append(record)

    def __send_delayed__(self) -> None:
        """
        A background thread that sends each message after a delay
        """
        while not self.closed:
            self.delay.wait(self.delay_time)

            if len(self.delayed) > 0:
                super().send(self.delayed.pop(0))

    def close(self):
        # Drain the queue of delayed messages at closure
        while len(self.delayed) > 0:
            # Set the delay event to trigger the next delayed record to be sent
            self.delay.set()
        self.closed = True
