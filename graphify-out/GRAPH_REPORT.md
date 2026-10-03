# Graph Report - speakon  (2026-10-03)

## Corpus Check
- 23 files · ~19,456 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 418 nodes · 782 edges · 18 communities (14 shown, 4 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 60 edges (avg confidence: 0.83)
- Token cost: 80,500 input · 0 output

## Community Hubs (Navigation)
- Config & Correction Helpers
- Window API & UI
- App Core & Startup
- Streaming Eval Tools
- Learning From Wispr
- Text Processing & Dictionary
- Docs & Features
- Streaming Dictation
- Hotkey Watcher
- FlowBar Overlay
- Speech Engine
- Microphone Capture
- Correction Watcher
- Learned Corrections Store
- Fake Mic Test Harness
- Graphify Integration
- Admin App Limitation

## God Nodes (most connected - your core abstractions)
1. `SpeakOn` - 38 edges
2. `Api` - 27 edges
3. `Dictation` - 19 edges
4. `SpeakOn` - 19 edges
5. `pywebview JS-to-Python api bridge` - 19 edges
6. `HotkeyWatcher` - 16 edges
7. `Microphone` - 14 edges
8. `Engine` - 11 edges
9. `SpeakOn weekly log` - 11 edges
10. `tick()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `Learn now (learn from Wispr Flow recordings)` --references--> `main()`  [INFERRED]
  README.md → tools/eval_wispr.py
- `loadDict()` --shares_data_with--> `dictionary_warnings()`  [INFERRED]
  ui/index.html → textproc.py
- `checkWarn()` --shares_data_with--> `dictionary_warnings()`  [INFERRED]
  ui/index.html → textproc.py
- `set_busy_priority()` --implements--> `Above-normal CPU priority only while dictating`  [INFERRED]
  speakon.py → tools/weekly_log.md
- `history_version change detection` --shares_data_with--> `SpeakOn`  [INFERRED]
  ui/index.html → speakon.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **SpeakOn voice-learning mechanisms** — readme_learn_from_wispr, readme_fix_after_dictating, readme_save_and_learn, learn_learn_fixes, corrections_editwatcher [INFERRED 0.85]
- **Low-latency dictation pipeline** — readme_transcribe_while_talking, readme_mic_lead_in, tools_weekly_log_v1_1_0, tools_weekly_log_v1_1_1, tools_weekly_log_v1_2_0 [INFERRED 0.85]
- **UI to Python Api bridge** — ui_index_api_bridge, ui_index_tick, speakon_api, requirements_pywebview [INFERRED 0.85]
- **Reducing dictation wait under CPU load** — tools_weekly_log_v1_2_1, tools_weekly_log_v1_2_2, ui_index_adaptive_polling, ui_index_tick, speakon_set_busy_priority, tools_weekly_log_real_median_wait [INFERRED 0.85]
- **Edit dictation and learn correction flow** — ui_index_saveedit, speakon_api_edit_history, learn_learned_learn_edit, ui_index_history_version [INFERRED 0.75]
- **Sound-alike snapping of dictionary words** — textproc_apply_custom_words, textproc_best_match, textproc_swallows_small_word, tools_weekly_log_sound_alike_snapping [INFERRED 0.85]

## Communities (18 total, 4 thin omitted)

### Community 0 - "Config & Correction Helpers"
Cohesion: 0.05
Nodes (12): combo_label(), hotkey_keys(), hotkey_label(), _levenshtein(), looks_like_correction(), INPUT, KEYBDINPUT, MOUSEINPUT (+4 more)

### Community 1 - "Window API & UI"
Cohesion: 0.07
Nodes (29): Edit dictation: Save & learn, Api, progress(), work(), entry_id(), clean(), v1.2.1 (sound-alike snapping fixes, idle polling fix), pywebview JS-to-Python api bridge (+21 more)

### Community 2 - "App Core & Startup"
Cohesion: 0.07
Nodes (10): history.json self-test check, foreground_app(), load_json(), make_tone(), modifiers_down(), save_json(), set_busy_priority(), set_start_with_windows() (+2 more)

### Community 3 - "Streaming Eval Tools"
Cohesion: 0.11
Nodes (19): main(), run(), load_textproc(), main(), wispr_texts(), align(), load(), main() (+11 more)

### Community 4 - "Learning From Wispr"
Cohesion: 0.10
Nodes (15): align(), apply_fixes(), diff_spans(), learn_fixes(), learn_from_wispr(), learn_lowercase(), learn_terms(), ngram_counts() (+7 more)

### Community 5 - "Text Processing & Dictionary"
Cohesion: 0.12
Nodes (18): apply_custom_words(), apply_replacements(), apply_spoken_commands(), _best_match(), collapse_stutters(), dictionary_warnings(), fix_midsentence_caps(), _keep_case() (+10 more)

### Community 6 - "Docs & Features"
Cohesion: 0.11
Nodes (25): Build-from-source agent prompt for Windows, Stand-alone SpeakOn.exe build (PyInstaller + build.ps1), Data folder C:\Users\<you>\SpeakOn, Dictionary rules (longest first, whole words, warnings), FluidVoice (Mac, GPL-3.0), Handy, Bottom-of-screen mic pill overlay, murmur (+17 more)

### Community 7 - "Streaming Dictation"
Cohesion: 0.15
Nodes (3): block_rms(), Dictation, transcribe_array()

### Community 8 - "Hotkey Watcher"
Cohesion: 0.19
Nodes (3): HotkeyWatcher, key_name(), matches()

### Community 9 - "FlowBar Overlay"
Cohesion: 0.18
Nodes (5): BITMAPINFOHEADER, BLENDFUNCTION, FlowBar, _font(), WNDCLASS

### Community 10 - "Speech Engine"
Cohesion: 0.14
Nodes (3): _Cancellable, Engine, is_english_only()

### Community 11 - "Microphone Capture"
Cohesion: 0.21
Nodes (3): Microphone, v1.2.0 (mic kept ready with lead-in), TOGGLES settings list

### Community 12 - "Correction Watcher"
Cohesion: 0.22
Nodes (3): EditWatcher, find_corrections(), _words()

### Community 15 - "Graphify Integration"
Cohesion: 0.50
Nodes (4): GRAPH_REPORT.md, graphify knowledge graph (graphify-out/), graphify query/path/explain commands, graphify update . (AST-only refresh)

## Knowledge Gaps
- **13 isolated node(s):** `INPUT`, `MOUSEINPUT`, `_U`, `graphify query/path/explain commands`, `graphify update . (AST-only refresh)` (+8 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 125 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SpeakOn` connect `App Core & Startup` to `Config & Correction Helpers`, `Window API & UI`, `Docs & Features`?**
  _High betweenness centrality (0.170) - this node is a cross-community bridge._
- **Why does `Api` connect `Window API & UI` to `Config & Correction Helpers`, `Docs & Features`?**
  _High betweenness centrality (0.153) - this node is a cross-community bridge._
- **Why does `SpeakOn` connect `Docs & Features` to `Streaming Eval Tools`, `Window API & UI`, `App Core & Startup`, `Microphone Capture`?**
  _High betweenness centrality (0.139) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `SpeakOn` (e.g. with `SpeakOn` and `history_version change detection`) actually correct?**
  _`SpeakOn` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Api` (e.g. with `SpeakOn` and `pywebview JS-to-Python api bridge`) actually correct?**
  _`Api` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `SpeakOn` (e.g. with `Api` and `SpeakOn`) actually correct?**
  _`SpeakOn` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `pywebview JS-to-Python api bridge` (e.g. with `pywebview` and `Api`) actually correct?**
  _`pywebview JS-to-Python api bridge` has 2 INFERRED edges - model-reasoned connections that need verification._