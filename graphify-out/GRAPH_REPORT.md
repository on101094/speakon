# Graph Report - speakon  (2026-10-02)

## Corpus Check
- Corpus is ~30,618 words - fits in a single context window. You may not need a graph.

## Summary
- 384 nodes · 698 edges · 17 communities (13 shown, 4 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 44 edges (avg confidence: 0.85)
- Token cost: 79,244 input · 0 output

## Community Hubs (Navigation)
- Correction Watcher
- App Core & Settings
- Config & Engine Module
- Docs & Features
- UI Bridge API
- Learning From Wispr
- Text Processing & Dictionary
- Streaming Dictation
- Hotkey Watcher
- Speech Engine
- Microphone Capture
- FlowBar Overlay
- Learned Corrections Store
- Fake Mic Test Harness
- Graphify Integration
- Admin App Limitation

## God Nodes (most connected - your core abstractions)
1. `SpeakOn` - 41 edges
2. `Api` - 25 edges
3. `Dictation` - 19 edges
4. `HotkeyWatcher` - 19 edges
5. `SpeakOn` - 19 edges
6. `Microphone` - 16 edges
7. `FlowBar` - 13 edges
8. `EditWatcher` - 11 edges
9. `Engine` - 11 edges
10. `process()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `Learn now (learn from Wispr Flow recordings)` --references--> `main()`  [INFERRED]
  README.md → tools/eval_wispr.py
- `v1.2.0: mic kept ready with 0.5 s lead-in` --references--> `Microphone`  [INFERRED]
  tools/weekly_log.md → mic.py
- `Bottom-of-screen mic pill overlay` --references--> `FlowBar`  [INFERRED]
  README.md → overlay.py
- `pywebview JS-Python API bridge (window.pywebview.api)` --references--> `Api`  [INFERRED]
  ui/index.html → speakon.py
- `checkWarn()` --shares_data_with--> `dictionary_warnings()`  [INFERRED]
  ui/index.html → textproc.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **SpeakOn voice-learning mechanisms** — readme_learn_from_wispr, readme_fix_after_dictating, readme_save_and_learn, learn_learn_fixes, corrections_editwatcher [INFERRED 0.85]
- **Low-latency dictation pipeline** — readme_transcribe_while_talking, readme_mic_lead_in, tools_weekly_log_v1_1_0, tools_weekly_log_v1_1_1, tools_weekly_log_v1_2_0 [INFERRED 0.85]
- **UI to Python Api bridge** — ui_index_api_bridge, ui_index_tick, speakon_api, requirements_pywebview [INFERRED 0.85]

## Communities (17 total, 4 thin omitted)

### Community 0 - "Correction Watcher"
Cohesion: 0.06
Nodes (12): EditWatcher, find_corrections(), _levenshtein(), looks_like_correction(), _words(), INPUT, KEYBDINPUT, MOUSEINPUT (+4 more)

### Community 1 - "App Core & Settings"
Cohesion: 0.08
Nodes (9): history.json self-test check, foreground_app(), load_json(), make_tone(), modifiers_down(), save_json(), set_start_with_windows(), SpeakOn (+1 more)

### Community 2 - "Config & Engine Module"
Cohesion: 0.10
Nodes (12): combo_label(), hotkey_keys(), hotkey_label(), main(), run(), align(), load(), main() (+4 more)

### Community 3 - "Docs & Features"
Cohesion: 0.09
Nodes (27): Build-from-source agent prompt for Windows, Stand-alone SpeakOn.exe build (PyInstaller + build.ps1), Data folder C:\Users\<you>\SpeakOn, FluidVoice (Mac, GPL-3.0), Handy, Bottom-of-screen mic pill overlay, NVIDIA Parakeet engine, Push-to-talk Ctrl + Win (hold or tap) (+19 more)

### Community 4 - "UI Bridge API"
Cohesion: 0.09
Nodes (12): pywebview, Api, pywebview JS-Python API bridge (window.pywebview.api), bindSwitch(), boot(), loadDict(), loadHistory(), loadSettings() (+4 more)

### Community 5 - "Learning From Wispr"
Cohesion: 0.10
Nodes (15): align(), apply_fixes(), diff_spans(), learn_fixes(), learn_from_wispr(), learn_lowercase(), learn_terms(), ngram_counts() (+7 more)

### Community 6 - "Text Processing & Dictionary"
Cohesion: 0.11
Nodes (20): Dictionary rules (longest first, whole words, warnings), murmur, apply_custom_words(), apply_replacements(), apply_spoken_commands(), _best_match(), collapse_stutters(), dictionary_warnings() (+12 more)

### Community 7 - "Streaming Dictation"
Cohesion: 0.13
Nodes (5): block_rms(), Dictation, transcribe_array(), progress(), work()

### Community 8 - "Hotkey Watcher"
Cohesion: 0.19
Nodes (3): HotkeyWatcher, key_name(), matches()

### Community 9 - "Speech Engine"
Cohesion: 0.14
Nodes (3): _Cancellable, Engine, is_english_only()

### Community 10 - "Microphone Capture"
Cohesion: 0.20
Nodes (3): Microphone, v1.2.0: mic kept ready with 0.5 s lead-in, TOGGLES settings list

### Community 11 - "FlowBar Overlay"
Cohesion: 0.21
Nodes (5): BITMAPINFOHEADER, BLENDFUNCTION, FlowBar, _font(), WNDCLASS

### Community 14 - "Graphify Integration"
Cohesion: 0.50
Nodes (4): GRAPH_REPORT.md, graphify knowledge graph (graphify-out/), graphify query/path/explain commands, graphify update . (AST-only refresh)

## Knowledge Gaps
- **13 isolated node(s):** `MOUSEINPUT`, `_U`, `INPUT`, `graphify query/path/explain commands`, `graphify update . (AST-only refresh)` (+8 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 128 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SpeakOn` connect `App Core & Settings` to `Correction Watcher`, `Docs & Features`, `Hotkey Watcher`, `Microphone Capture`, `FlowBar Overlay`?**
  _High betweenness centrality (0.194) - this node is a cross-community bridge._
- **Why does `Api` connect `UI Bridge API` to `Correction Watcher`, `Docs & Features`, `Text Processing & Dictionary`, `Streaming Dictation`?**
  _High betweenness centrality (0.169) - this node is a cross-community bridge._
- **Why does `SpeakOn` connect `Docs & Features` to `App Core & Settings`, `Microphone Capture`, `UI Bridge API`, `Text Processing & Dictionary`?**
  _High betweenness centrality (0.120) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `SpeakOn` (e.g. with `SpeakOn` and `EditWatcher`) actually correct?**
  _`SpeakOn` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Api` (e.g. with `SpeakOn` and `pywebview JS-Python API bridge (window.pywebview.api)`) actually correct?**
  _`Api` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `HotkeyWatcher` (e.g. with `Push-to-talk Ctrl + Win (hold or tap)` and `SpeakOn`) actually correct?**
  _`HotkeyWatcher` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `SpeakOn` (e.g. with `Api` and `SpeakOn`) actually correct?**
  _`SpeakOn` has 2 INFERRED edges - model-reasoned connections that need verification._