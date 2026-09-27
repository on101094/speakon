"""The microphone, kept ready so the first word is never cut off.

Opening a microphone on Windows takes 100-200 ms, and people start talking the moment
they press the shortcut (often a little before the second key is down). So by default
the stream stays open and the last PREROLL_SECONDS of audio are kept in memory, in a
small ring that is constantly overwritten. When dictation starts, that half second
goes in front of the recording. Nothing is saved or sent anywhere while idle.

With keep_open off, the microphone is opened on each press and closed after, like before.
"""

import collections
import logging
import threading
import time

import sounddevice as sd

import engine as eng

log = logging.getLogger("speakon")
PREROLL_SECONDS = 0.5
PREROLL_BLOCKS = int(PREROLL_SECONDS * eng.SAMPLE_RATE / eng.BLOCK)
STALE_SECONDS = 1.0        # no audio for this long: the stream died (sleep, unplugged) - reopen


class Microphone:
    def __init__(self, device=None, keep_open=True, factory=None):
        self.device = device
        self.keep_open = keep_open
        self.factory = factory     # tests: callable(callback) -> stream-like object
        self.stream = None
        self.sink = None
        self.ring = collections.deque(maxlen=PREROLL_BLOCKS)
        self.last = 0.0
        self.lock = threading.Lock()
        self.opened_at = 0.0

    def _callback(self, indata, frames, t, status):
        block = indata[:, 0].copy()
        self.last = time.time()
        with self.lock:
            if self.sink:
                self.sink(block)
            else:
                self.ring.append(block)

    def _open(self):
        self._close()
        self.ring.clear()
        if self.factory:
            self.stream = self.factory(self._callback)
        else:
            self.stream = sd.InputStream(samplerate=eng.SAMPLE_RATE, channels=1, dtype="float32",
                                         blocksize=eng.BLOCK, device=self.device, callback=self._callback)
        self.stream.start()
        self.opened_at = self.last = time.time()

    def _close(self):
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

    def _alive(self):
        return self.stream is not None and time.time() - self.last < STALE_SECONDS

    def warm(self):
        """Open the idle stream now (at start-up and after settings change)."""
        if not self.keep_open:
            return
        try:
            self._open()
            log.info("microphone ready (kept open, %.1f s lead-in)", PREROLL_SECONDS)
        except Exception as e:
            log.warning("could not open the microphone yet: %s", e)

    def begin(self, sink):
        """Start sending audio to sink(block). Earlier audio (up to half a second) goes first.
        Returns the lead-in length in seconds. Raises if the microphone can't be opened."""
        if not (self.keep_open and self._alive()):
            if self.keep_open and self.stream:
                log.info("microphone stream had stopped - reopening")
            self._open()
        with self.lock:
            lead = list(self.ring)
            self.ring.clear()
            for block in lead:
                sink(block)
            self.sink = sink
        return len(lead) * eng.BLOCK / eng.SAMPLE_RATE

    def end(self):
        with self.lock:
            self.sink = None
            self.ring.clear()
        if not self.keep_open:
            self._close()

    def configure(self, device=None, keep_open=True):
        changed = device != self.device or keep_open != self.keep_open
        self.device, self.keep_open = device, keep_open
        if changed and self.sink is None:
            self._close()
            self.warm()

    def close(self):
        with self.lock:
            self.sink = None
        self._close()

