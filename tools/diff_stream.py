"""Where does the live pipeline lose accuracy vs pause-only pieces? Saves both outputs per clip."""
import json, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..")); sys.path.insert(0, os.path.dirname(__file__))
import engine as E, learn, config as C
from eval_stream import run
from eval_wispr import norm, align
n = int(sys.argv[1]); out = sys.argv[2]
clips = learn.wispr_clips(); random.Random(7).shuffle(clips); clips = clips[:n]
eng = E.Engine(C.MODELS_DIR); eng.load("parakeet-v2")
rows = []
for c in clips:
    a, b = run(eng, c["audio"], False), run(eng, c["audio"], True)
    ref = norm(c["ref"]); ea, _ = align(ref, norm(a)); eb, _ = align(ref, norm(b))
    rows.append({"ref": c["ref"], "pause": a, "live": b, "err_pause": ea, "err_live": eb, "secs": len(c["audio"]) / 16000})
    print(len(rows), ea, eb, flush=True)
json.dump(rows, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
