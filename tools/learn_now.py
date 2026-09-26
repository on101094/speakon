"""Run the 'Your voice -> Learn now' step from the command line and save the result."""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config as C, engine as E, learn

eng = E.Engine(C.MODELS_DIR)
eng.load(sys.argv[1] if len(sys.argv) > 1 else "parakeet-v2")
t0 = time.time()
last = [0]
def progress(done, total, msg):
    if done - last[0] >= 50 or done == total:
        last[0] = done
        print(f"{done}/{total}  {time.time() - t0:.0f}s", flush=True)
r = learn.learn_from_wispr(eng, lambda a: E.transcribe_array(eng, a), progress)
L = learn.Learned(C.LEARNED_FILE)
L.merge_fixes(r["fixes"], "Wispr Flow")
L.data["terms"] = r["terms"][:80]
L.data["clips"] = r["clips"]
L.data["report"] = (f"On recordings it did not learn from, mistakes went from {r['wer_before'] * 100:.1f}% "
                    f"to {r['wer_after'] * 100:.1f}% of words.")
L.save()
print("clips", r["clips"], "| WER before", round(r["wer_before"] * 100, 2), "after", round(r["wer_after"] * 100, 2))
print("fixes:", [(f["heard"], f["wanted"], f["count"], f["precision"]) for f in r["fixes"]])
print("terms:", r["terms"][:80])
