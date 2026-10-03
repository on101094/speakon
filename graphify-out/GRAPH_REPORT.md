# Graph Report - speakon  (2026-10-03)

## Corpus Check
- 30 files · ~30,790 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: (none) 3, .ico 1)

## Summary
- 452 nodes · 766 edges · 27 communities (19 shown, 8 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 44 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `56410c40`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- speakon.py
- SpeakOn
- engine.py
- SpeakOn
- Api
- learn.py
- textproc.py
- Dictation
- HotkeyWatcher
- Engine
- Microphone
- FlowBar
- Learned
- FakeMic
- graphify knowledge graph (graphify-out/)
- Cannot type into administrator apps
- What You Must Do When Invoked
- graphify reference: extra exports and benchmark
- graphify reference: query, path, explain
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- CLAUDE.md
- extraction-spec.md

## God Nodes (most connected - your core abstractions)
1. `SpeakOn` - 41 edges
2. `Api` - 27 edges
3. `Dictation` - 19 edges
4. `HotkeyWatcher` - 19 edges
5. `SpeakOn` - 19 edges
6. `Microphone` - 16 edges
7. `FlowBar` - 13 edges
8. `What You Must Do When Invoked` - 12 edges
9. `EditWatcher` - 11 edges
10. `Engine` - 11 edges

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

## Communities (27 total, 8 thin omitted)

### Community 0 - "speakon.py"
Cohesion: 0.05
Nodes (15): EditWatcher, find_corrections(), _levenshtein(), looks_like_correction(), _words(), INPUT, KEYBDINPUT, MOUSEINPUT (+7 more)

### Community 1 - "SpeakOn"
Cohesion: 0.08
Nodes (6): history.json self-test check, modifiers_down(), save_json(), set_start_with_windows(), SpeakOn, work()

### Community 2 - "engine.py"
Cohesion: 0.10
Nodes (12): combo_label(), hotkey_keys(), hotkey_label(), main(), run(), align(), load(), main() (+4 more)

### Community 3 - "SpeakOn"
Cohesion: 0.11
Nodes (25): Build-from-source agent prompt for Windows, Stand-alone SpeakOn.exe build (PyInstaller + build.ps1), Data folder C:\Users\<you>\SpeakOn, FluidVoice (Mac, GPL-3.0), Handy, Bottom-of-screen mic pill overlay, NVIDIA Parakeet engine, Push-to-talk Ctrl + Win (hold or tap) (+17 more)

### Community 4 - "Api"
Cohesion: 0.07
Nodes (17): Edit dictation: Save & learn, pywebview, Api, progress(), work(), entry_id(), pywebview JS-Python API bridge (window.pywebview.api), bindSwitch() (+9 more)

### Community 5 - "learn.py"
Cohesion: 0.10
Nodes (15): align(), apply_fixes(), diff_spans(), learn_fixes(), learn_from_wispr(), learn_lowercase(), learn_terms(), ngram_counts() (+7 more)

### Community 6 - "textproc.py"
Cohesion: 0.11
Nodes (20): Dictionary rules (longest first, whole words, warnings), murmur, apply_custom_words(), apply_replacements(), apply_spoken_commands(), _best_match(), collapse_stutters(), dictionary_warnings() (+12 more)

### Community 7 - "Dictation"
Cohesion: 0.16
Nodes (3): block_rms(), Dictation, transcribe_array()

### Community 8 - "HotkeyWatcher"
Cohesion: 0.19
Nodes (3): HotkeyWatcher, key_name(), matches()

### Community 9 - "Engine"
Cohesion: 0.14
Nodes (3): _Cancellable, Engine, is_english_only()

### Community 10 - "Microphone"
Cohesion: 0.20
Nodes (3): Microphone, v1.2.0: mic kept ready with 0.5 s lead-in, TOGGLES settings list

### Community 11 - "FlowBar"
Cohesion: 0.18
Nodes (5): BITMAPINFOHEADER, BLENDFUNCTION, FlowBar, _font(), WNDCLASS

### Community 14 - "graphify knowledge graph (graphify-out/)"
Cohesion: 0.50
Nodes (4): GRAPH_REPORT.md, graphify knowledge graph (graphify-out/), graphify query/path/explain commands, graphify update . (AST-only refresh)

### Community 17 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 18 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 19 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 20 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 21 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 22 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

## Knowledge Gaps
- **55 isolated node(s):** `MOUSEINPUT`, `_U`, `INPUT`, `graphify`, `Usage` (+50 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 180 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SpeakOn` connect `SpeakOn` to `speakon.py`, `SpeakOn`, `HotkeyWatcher`, `Microphone`, `FlowBar`?**
  _High betweenness centrality (0.142) - this node is a cross-community bridge._
- **Why does `Api` connect `Api` to `speakon.py`, `SpeakOn`, `textproc.py`?**
  _High betweenness centrality (0.123) - this node is a cross-community bridge._
- **Why does `SpeakOn` connect `SpeakOn` to `SpeakOn`, `Microphone`, `Api`, `textproc.py`?**
  _High betweenness centrality (0.088) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `SpeakOn` (e.g. with `SpeakOn` and `EditWatcher`) actually correct?**
  _`SpeakOn` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Api` (e.g. with `SpeakOn` and `pywebview JS-Python API bridge (window.pywebview.api)`) actually correct?**
  _`Api` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `HotkeyWatcher` (e.g. with `Push-to-talk Ctrl + Win (hold or tap)` and `SpeakOn`) actually correct?**
  _`HotkeyWatcher` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `SpeakOn` (e.g. with `Api` and `SpeakOn`) actually correct?**
  _`SpeakOn` has 2 INFERRED edges - model-reasoned connections that need verification._