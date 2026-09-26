"""Accuracy of the full live pipeline (pieces + previews + release) on the user's Wispr recordings.
Previews are simulated every 0.45 s of audio as if the computer were instant, so this measures
accuracy, not speed.  usage: python tools/eval_stream.py <wispr_eval dir> <n clips> [promote=0|1 ...]"""
import json, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import engine as E
from eval_wispr import norm, align, load, MODELS_DIR


def run(eng, audio, previews=True):
    d = E.Dictation(eng, live_preview=True, start_worker=False)
    for i in range(0, len(audio) - E.BLOCK + 1, E.BLOCK):
        d.feed(audio[i:i + E.BLOCK])
        if (i // E.BLOCK) % 15 == 14:
            while not d.jobs.empty():
                d._do(*d.jobs.get())
                d.chunks_done += 1
            if previews:
                d.last_preview = 0
                d._maybe_preview()
    while not d.jobs.empty():
        d._do(*d.jobs.get())
    d.finishing = True
    if len(d.blocks) > d.done_to:
        if len(d.blocks) - d.done_to <= E.SHORT_TAIL_BLOCKS:
            d.spec = None                      # same rule as the app's release step
        d._do(d.done_to, len(d.blocks), d.threshold())
    return d.committed_text()


def main():
    src, n = sys.argv[1], int(sys.argv[2])
    meta = [m for m in json.load(open(os.path.join(src, "meta.json"), encoding="utf-8"))
            if m["lang"] == "en" and m["asr"] and 2 <= m["secs"] <= 60]
    random.Random(7).shuffle(meta)
    clips = meta[:n]
    eng = E.Engine(MODELS_DIR); eng.load("parakeet-v2")
    audios = [load(m["wav"]) for m in clips]
    for arg in sys.argv[3:] or ["gap=5,ctx=50"]:
        cfg = dict(kv.split("=") for kv in arg.split(","))
        E.PREVIEW_GAP = int(cfg.get("gap", 5)); E.REMAINDER_CONTEXT = int(cfg.get("ctx", 50))
        E.PROMOTE_BLOCKS = int(cfg.get("promote", 200))
        errs = words = 0
        for m, a in zip(clips, audios):
            ref = norm(m["asr"]); e, _ = align(ref, norm(run(eng, a, cfg.get("preview", "1") == "1"))); errs += e; words += len(ref)
        print(f"{arg}: WER {errs / words * 100:.2f}%", flush=True)


if __name__ == "__main__":
    main()
