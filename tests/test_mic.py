import threading
import time

import mic


class FakeStream:
    opened = []

    def __init__(self, callback):
        time.sleep(0.05)            # opening a real device takes a while
        self.closed = False
        FakeStream.opened.append(self)

    def start(self):
        pass

    def stop(self):
        pass

    def close(self):
        self.closed = True


def test_warm_and_begin_at_the_same_time_open_one_stream():
    for _ in range(20):
        FakeStream.opened = []
        m = mic.Microphone(keep_open=True, factory=FakeStream)
        got = []
        warm = threading.Thread(target=m.warm)
        warm.start()
        m.begin(got.append)          # the key pressed while start-up is still opening the microphone
        warm.join()
        live = [s for s in FakeStream.opened if not s.closed]
        assert len(live) == 1 and m.stream is live[0]
