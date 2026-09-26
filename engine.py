"""Speech engines and the streaming dictation pipeline.

Engines
  - Parakeet TDT v3 / v2 (NVIDIA, via onnx-asr, int8 on CPU) - FluidVoice/Handy's fast engine.
  - Whisper tiny..large-v3-turbo (faster-whisper, int8) - SpeakType's engine, 99 languages.

Streaming ("transcribe while you talk")
  Audio arrives in 30 ms blocks. When the speaker pauses (~0.55 s of quiet) after at
  least 4 s of speech, the finished piece is transcribed in the background, so after
  the key is released only the last piece is left.

  Each piece is transcribed together with the ~3 s of audio before it ("context").
  With word timings we keep only the words that belong to the new piece, and the
  context tells us how the model punctuates the join: if it hears one continuing
  sentence, the full stop the previous piece ended with is removed and the new piece
  continues in lower case. Without this, every pause became ". Capital".
"""

import os
import queue
import threading
import time
from pathlib import Path

import numpy as np

from textproc import COMMON_WORDS

SAMPLE_RATE = 16000
BLOCK = 480                 # 30 ms
PAUSE_BLOCKS = 18           # 540 ms of quiet = a pause we can cut at
MIN_CHUNK_BLOCKS = 200      # 6 s - tuned on the user's recordings: fewer joins, fewer errors
MAX_CHUNK_BLOCKS = 800      # 24 s - force a cut at the quietest spot
PREVIEW_GAP = 5             # a preview ends at a quiet gap of this many blocks (150 ms)
REMAINDER_CONTEXT = 100     # context for the words after a reused preview (3 s: tuned on the user's recordings)
PROMOTE_BLOCKS = 200        # lock in a preview once it covers 6 s of finished words
CONTEXT_BLOCKS = 100        # 3 s of earlier audio in front of each piece
PAD_BLOCKS = 7              # keep 210 ms of quiet around speech
SENTENCE_END = ".?!"
JOIN_PUNCT = ".?!,;:"

MODELS = {
    "parakeet-v2": ("parakeet", "nemo-parakeet-tdt-0.6b-v2",
                    "Parakeet v2 · English · most accurate on your voice (recommended)"),
    "parakeet-v3": ("parakeet", "nemo-parakeet-tdt-0.6b-v3",
                    "Parakeet v3 · 25 European languages · fast"),
    "large-v3-turbo": ("whisper", "large-v3-turbo",
                       "Whisper Large v3 Turbo · 99 languages · most robust, slow on this PC"),
    "medium": ("whisper", "medium", "Whisper Medium · 99 languages · slow on this PC"),
    "small": ("whisper", "small", "Whisper Small · 99 languages"),
    "small.en": ("whisper", "small.en", "Whisper Small · English only"),
    "base.en": ("whisper", "base.en", "Whisper Base · English only · light"),
    "tiny": ("whisper", "tiny", "Whisper Tiny · 99 languages · lowest accuracy"),
}


class _Cancellable:
    """Wraps an onnxruntime session so a running call can be stopped from another thread."""

    def __init__(self, session):
        self._session = session
        self._opts = None

    def run(self, outputs, feeds, run_options=None):
        import onnxruntime as ort
        self._opts = ort.RunOptions()
        try:
            return self._session.run(outputs, feeds, self._opts)
        finally:
            self._opts = None

    def cancel(self):
        opts = self._opts
        if opts is not None:
            opts.terminate = True

    def __getattr__(self, name):
        return getattr(self._session, name)


def is_english_only(model_id):
    return model_id == "parakeet-v2" or model_id.endswith(".en")


class Engine:
    """Holds one loaded model. All calls are serialised with a lock."""

    def __init__(self, models_dir):
        self.models_dir = Path(models_dir)
        self.model_id = None
        self.kind = None
        self.model = None
        self.model_ts = None
        self.lock = threading.Lock()
        self.ready = threading.Event()
        self.error = None
        self.encoder = None
        self.preview_running = False

    def load(self, model_id, on_status=lambda s: None):
        kind, name, _ = MODELS[model_id]
        with self.lock:
            if self.model_id == model_id and self.model is not None:
                return
            self.ready.clear()
            self.error = None
            self.model = self.model_ts = None
            target = self.models_dir / name
            first = not target.exists()
            on_status(f"Downloading {model_id} (one time)…" if first else f"Loading {model_id}…")
            threads = 3 if kind == "parakeet" else max(2, (os.cpu_count() or 4) // 2)  # measured: more is slower
            try:
                if kind == "parakeet":
                    import onnx_asr
                    import onnxruntime as ort
                    opts = ort.SessionOptions()
                    opts.intra_op_num_threads = threads
                    self.model = onnx_asr.load_model(name, str(target), quantization="int8", sess_options=opts)
                    self.model_ts = self.model.with_timestamps()
                    self.encoder = self.model.asr._encoder = _Cancellable(self.model.asr._encoder)
                else:
                    from faster_whisper import WhisperModel
                    from faster_whisper.utils import download_model
                    try:
                        path = download_model(name, output_dir=str(target), local_files_only=True)
                    except Exception:
                        path = download_model(name, output_dir=str(target))
                    self.model = WhisperModel(path, device="cpu", compute_type="int8", cpu_threads=threads)
                self.kind, self.model_id = kind, model_id
                self._words(np.zeros(SAMPLE_RATE, dtype=np.float32), None, "", "")  # warm-up
            except Exception as e:
                self.error = str(e)
                self.model_id = None
                on_status(f"Model failed: {e}")
                self.ready.set()
                raise
            self.ready.set()
            on_status(f"Ready · {model_id}")

    def _words(self, audio, language, prompt, hotwords):
        """[(text_with_leading_space, start_seconds), ...] - punctuation stays on its word."""
        if self.kind == "parakeet":
            r = self.model_ts.recognize(audio, sample_rate=SAMPLE_RATE)
            words = []
            for tok, t in zip(r.tokens or [], r.timestamps or []):
                if not words or tok.startswith(" ") or tok.startswith("▁"):
                    words.append([tok.replace("▁", " "), float(t)])
                else:
                    words[-1][0] += tok
            return [(w, t) for w, t in words]
        segments, _ = self.model.transcribe(
            audio, language=language, beam_size=5, vad_filter=False,
            condition_on_previous_text=False, word_timestamps=True,
            initial_prompt=prompt or None, hotwords=hotwords or None)
        out = []
        for s in segments:
            for w in s.words or []:
                out.append((w.word, float(w.start)))
        return out

    def _check(self, language):
        self.ready.wait()
        if self.model is None:
            raise RuntimeError(self.error or "no model loaded")
        return None if self.kind == "parakeet" or is_english_only(self.model_id) else language

    def words(self, audio, language=None, prompt="", hotwords="", preview=False):
        language = self._check(language)
        with self.lock:
            self.preview_running = preview
            try:
                return self._words(audio, language, prompt, hotwords)
            finally:
                self.preview_running = False

    def cancel_preview(self):
        """Stop a live-preview transcription that is still running (the key was released)."""
        if self.preview_running and self.encoder is not None:
            self.encoder.cancel()

    def transcribe(self, audio, language=None, prompt="", hotwords=""):
        return "".join(w for w, _ in self.words(audio, language, prompt, hotwords)).strip()


def block_rms(block):
    return float(np.sqrt(np.mean(block * block))) if len(block) else 0.0


class Dictation:
    """One recording. feed() is called from the audio thread with 30 ms blocks.

    Pieces are cut at pauses and transcribed in order by one worker thread. Between
    pieces the worker keeps a "preview" of the words since the last cut, ending at a
    small gap between words. When a piece or the final tail is due, a matching preview
    is kept as-is and only the words after it are transcribed - that is what makes the
    text appear almost as soon as the key is released.
    """

    def __init__(self, engine, language=None, hotwords="", live_preview=True, on_preview=None, start_worker=True):
        self.engine = engine
        self.language = language
        self.hotwords = hotwords
        self.live_preview = live_preview
        self.on_preview = on_preview or (lambda text: None)
        self.blocks, self.rms = [], []
        self.committed = 0          # audio side: where the next piece starts
        self.done_to = 0            # worker side: audio covered by finished pieces
        self.quiet = 0
        self.seg_peak = 0.0
        self.noise = 0.003
        self.pieces = []
        self.nchunks = 0
        self.chunks_done = 0
        self.jobs = queue.Queue()
        self.cancelled = False
        self.finishing = False
        self.last_preview = 0.0
        self.error = None
        self.spec = None
        self.reused_preview = False
        self.cut_lock = threading.Lock()
        self.worker = threading.Thread(target=self._work, daemon=True)
        if start_worker:
            self.worker.start()

    # ----- audio side
    def threshold(self):
        return max(0.004, self.noise * 3.0)

    def feed(self, block):
        r = block_rms(block)
        self.blocks.append(block)
        self.rms.append(r)
        n = len(self.blocks)
        if n % 10 == 0:  # adaptive noise floor: quiet end of the last ~10 s
            self.noise = max(0.0008, float(np.percentile(self.rms[-333:], 10)))
        thr = self.threshold()
        self.quiet = self.quiet + 1 if r < thr else 0
        self.seg_peak = max(self.seg_peak, r)
        with self.cut_lock:
            seg = n - self.committed
            if seg < MIN_CHUNK_BLOCKS or self.finishing:
                return
            if self.quiet >= PAUSE_BLOCKS and self.seg_peak > thr * 2:
                self._commit(n - PAUSE_BLOCKS // 2)
            elif seg >= MAX_CHUNK_BLOCKS:
                window = np.convolve(np.array(self.rms[n - 166:n]), np.ones(5) / 5, mode="same")
                self._commit(n - 166 + int(np.argmin(window)))

    def _commit(self, cut):
        start = self.committed
        self.committed = cut
        self.seg_peak = 0.0
        self.nchunks += 1
        self.jobs.put((start, cut, self.threshold()))

    # ----- worker side
    def _voiced(self, a, b, thr):
        return [i for i in range(a, b) if self.rms[i] >= thr]

    def _piece(self, start, end, thr, context=CONTEXT_BLOCKS, preview=False):
        """Transcribe blocks [start, end) as the next piece.
        Returns (text, new text for the previous piece or None). Does not change state."""
        voiced = self._voiced(start, end, thr)
        if len(voiced) < 4:                       # < 120 ms above the noise: silence
            return "", None
        end = min(end, voiced[-1] + 1 + PAD_BLOCKS)
        prev = self.pieces[-1] if self.pieces else None
        if prev:
            ctx = max(0, start - context)
        else:
            # never clip the first word: only skip a long silence before speaking
            if voiced[0] - start > 50:
                start = voiced[0] - 20
            ctx = start
        audio = np.concatenate(self.blocks[ctx:end])
        if len(audio) < SAMPLE_RATE // 2:          # engines like at least ~0.5 s
            audio = np.concatenate([audio, np.zeros(SAMPLE_RATE // 2 - len(audio), np.float32)])
        prompt = self.committed_text()[-200:]
        words = self.engine.words(audio, self.language, prompt, self.hotwords, preview=preview)
        if not prev:
            return "".join(w for w, _ in words).strip(), None

        ctx_sec = (start - ctx) * BLOCK / SAMPLE_RATE
        split = next((i for i, (_, t) in enumerate(words) if t >= ctx_sec - 0.12), len(words))
        # line the words up too: the new part starts right after the last word already written
        key = lambda w: "".join(c for c in w.lower() if c.isalnum())
        prev_words = prev.split()
        last = key(prev_words[-1]) if prev_words else ""
        if last:
            for i in range(min(split + 1, len(words)), 0, -1):
                if words[i - 1][1] < ctx_sec - 1.6:
                    break
                if key(words[i - 1][0]) == last:
                    split = i
                    break
        new = "".join(w for w, _ in words[split:]).strip()
        prev_fixed = None
        if split > 0:
            # how does the model punctuate the join when it hears both sides?
            join = words[split - 1][0].rstrip()
            punct = join[len(join.rstrip(JOIN_PUNCT)):]
            prev_fixed = prev.rstrip(JOIN_PUNCT) + punct
            if new and punct[-1:] in SENTENCE_END and new[0].islower():
                new = new[0].upper() + new[1:]
            elif new and punct[-1:] not in SENTENCE_END:
                # mid-sentence join: "processor And I can" -> "processor and I can"
                first = new.split(" ", 1)[0]
                bare = first.strip(",.;:!?").lower()
                if first[:1].isupper() and bare in COMMON_WORDS and bare != "i" and not bare.startswith("i'"):
                    new = new[0].lower() + new[1:]
        return new, prev_fixed

    def _store(self, text, prev_fixed, end):
        if prev_fixed is not None and self.pieces:
            self.pieces[-1] = prev_fixed
        self.pieces.append(text)
        self.done_to = end

    def _do(self, start, end, thr):
        """Finish audio [start, end), reusing the preview when it matches."""
        spec, self.spec = self.spec, None
        if (spec and spec["start"] == start == self.done_to and spec["n"] == len(self.pieces)
                and spec["end"] <= end and spec["text"]):
            self.reused_preview = True
            self._store(spec["text"], spec["prev_fixed"], spec["end"])
            start = spec["end"]
            if not self._voiced(start, end, thr):
                self.done_to = end
                return
            context = REMAINDER_CONTEXT
        else:
            context = CONTEXT_BLOCKS
        text, prev_fixed = "", None
        if not self.cancelled:
            try:
                text, prev_fixed = self._piece(start, end, thr, context)
            except Exception as e:
                self.error = e
        self._store(text, prev_fixed, end)

    def committed_text(self):
        return " ".join(p for p in self.pieces if p)

    def _work(self):
        while True:
            try:
                job = self.jobs.get(timeout=0.08)
            except queue.Empty:
                self._maybe_preview()
                continue
            if job is None:
                return
            if job == "finish":
                n = len(self.blocks)
                if n > self.done_to and not self.cancelled:
                    self._do(self.done_to, n, self.threshold())
                return
            start, end, thr = job
            self._do(start, end, thr)
            self.chunks_done += 1
            if not self.finishing and not self.cancelled:
                self.on_preview(self.committed_text())

    def _maybe_preview(self):
        """Transcribe the words since the last cut, exactly as the final step would,
        ending at the latest small gap between words."""
        if not self.live_preview or self.finishing or self.cancelled or not self.engine.ready.is_set():
            return
        n = len(self.blocks)
        start = self.done_to
        if start != self.committed:
            return                                  # a piece is queued: let it run first
        tail = n - start
        if time.time() - self.last_preview < 0.45 or tail < 20 or tail > 400:   # 0.6 s .. 12 s
            return
        thr = self.threshold()
        if self.spec and self.spec["start"] == start and not self._voiced(self.spec["end"], n, thr):
            return                                  # nothing new said since the last preview
        self.last_preview = time.time()
        end = n
        for e in range(n, start + 20, -1):          # latest gap between words
            if all(r < thr for r in self.rms[e - PREVIEW_GAP:e]):
                end = e - PREVIEW_GAP // 2
                break
        try:
            text, prev_fixed = self._piece(start, end, thr, preview=True)
        except Exception:
            return                                  # cancelled at release, or failed
        if self.finishing:
            return
        self.spec = {"start": start, "end": end, "text": text, "prev_fixed": prev_fixed, "n": len(self.pieces)}
        if PROMOTE_BLOCKS and end - start >= PROMOTE_BLOCKS and text:
            # 6 s+ of finished words: lock them in, so later previews (and the release) stay short
            with self.cut_lock:
                if self.committed == start and not self.finishing:
                    self.committed = end
                    self.seg_peak = 0.0
                    self.nchunks += 1
                    self.chunks_done += 1
                    self._store(text, prev_fixed, end)
                    self.spec = None
        if not self.finishing and not self.cancelled:
            if self.spec is None:
                self.on_preview(self.committed_text())
            else:
                shown = list(self.pieces)
                if prev_fixed is not None and shown:
                    shown[-1] = prev_fixed
                self.on_preview(" ".join(p for p in shown + [text] if p))

    # ----- control
    def finish(self):
        """Call after the audio stream has stopped. Blocks until all text is ready."""
        self.finishing = True
        self.engine.cancel_preview()
        self.jobs.put("finish")
        self.worker.join()
        return self.committed_text()

    def cancel(self):
        self.cancelled = True
        self.finishing = True
        self.jobs.put(None)

    def audio(self):
        return np.concatenate(self.blocks) if self.blocks else np.zeros(0, np.float32)

    @property
    def seconds(self):
        return len(self.blocks) * BLOCK / SAMPLE_RATE


def transcribe_array(engine, audio, language=None, hotwords="", progress=None):
    """Transcribe a whole recording (audio file, or a saved dictation) with the same pipeline."""
    d = Dictation(engine, language, hotwords, live_preview=False)
    for i in range(0, len(audio) - BLOCK + 1, BLOCK):
        d.feed(audio[i:i + BLOCK])
    d.finishing = True
    total = d.nchunks + 1
    d.jobs.put("finish")
    while d.worker.is_alive():
        d.worker.join(0.3)
        if progress:
            progress(min(d.chunks_done, total), total)
    return d.committed_text()


def load_audio_file(path):
    import av
    out = []
    with av.open(str(path)) as container:
        stream = container.streams.audio[0]
        resampler = av.AudioResampler(format="flt", layout="mono", rate=SAMPLE_RATE)
        for frame in container.decode(stream):
            for f in resampler.resample(frame):
                out.append(f.to_ndarray().reshape(-1))
        for f in resampler.resample(None):
            out.append(f.to_ndarray().reshape(-1))
    return np.concatenate(out).astype(np.float32) if out else np.zeros(0, np.float32)


def save_wav(path, audio):
    import wave
    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())
