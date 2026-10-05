- Faster after you let go: when you pause for a moment before releasing the key, the text is usually already finished. SpeakOn now starts transcribing as soon as you stop speaking (about 0.2 s of quiet) and, if nothing new was said, uses that result instead of transcribing the same words again. Same words as before: the result is reused only when it heard exactly the audio the final step would.
- On GitHub's Windows test machine, with synthesized speech, the wait after letting go went from 0.07-0.33 s (average over four clips, depending on how long you pause) to under 0.01 s, with the same or better word accuracy. If you let go while still speaking, nothing changes.

Download SpeakOn-1.2.4-windows-x64.zip, unzip, run SpeakOn.exe. Windows only.
