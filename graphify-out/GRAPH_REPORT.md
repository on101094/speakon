# Graph Report - speakon  (2026-10-03)

## Corpus Check
- 22 files · ~19,802 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: (none) 3, .ico 1)

## Summary
- 446 nodes · 847 edges · 22 communities (16 shown, 6 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 65 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7c47df5f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Api
- SpeakOn
- engine.py
- learn.py
- textproc.py
- SpeakOn
- Dictation
- Hotkey Watcher
- FlowBar
- Engine
- Microphone
- Store
- Learned
- FakeMic
- graphify knowledge graph (graphify-out/)
- Cannot type into administrator apps
- corrections.py
- EditWatcher
- sendinput.py
- .__init__

## God Nodes (most connected - your core abstractions)
1. `SpeakOn` - 38 edges
2. `Api` - 25 edges
3. `Store` - 21 edges
4. `Dictation` - 19 edges
5. `HotkeyWatcher` - 19 edges
6. `pywebview JS-to-Python api bridge` - 19 edges
7. `SpeakOn` - 19 edges
8. `Microphone` - 17 edges
9. `Learned` - 15 edges
10. `FlowBar` - 13 edges

## Surprising Connections (you probably didn't know these)
- `set_busy_priority()` --implements--> `Above-normal CPU priority only while dictating`  [INFERRED]
  speakon.py → tools/weekly_log.md
- `history_version change detection` --shares_data_with--> `SpeakOn`  [INFERRED]
  ui/index.html → speakon.py
- `checkWarn()` --shares_data_with--> `dictionary_warnings()`  [INFERRED]
  ui/index.html → textproc.py
- `loadDict()` --shares_data_with--> `dictionary_warnings()`  [INFERRED]
  ui/index.html → textproc.py
- `Learn now (learn from Wispr Flow recordings)` --references--> `main()`  [INFERRED]
  README.md → tools/eval_wispr.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Edit dictation and learn correction flow** — ui_index_saveedit, speakon_api_edit_history, learn_learned_learn_edit, ui_index_history_version [INFERRED 0.75]
- **Reducing dictation wait under CPU load** — tools_weekly_log_v1_2_1, tools_weekly_log_v1_2_2, ui_index_adaptive_polling, ui_index_tick, speakon_set_busy_priority, tools_weekly_log_real_median_wait [INFERRED 0.85]
- **Sound-alike snapping of dictionary words** — textproc_apply_custom_words, textproc_best_match, textproc_swallows_small_word, tools_weekly_log_sound_alike_snapping [INFERRED 0.85]
- **SpeakOn voice-learning mechanisms** — readme_learn_from_wispr, readme_fix_after_dictating, readme_save_and_learn, learn_learn_fixes, corrections_editwatcher [INFERRED 0.85]
- **Low-latency dictation pipeline** — readme_transcribe_while_talking, readme_mic_lead_in, tools_weekly_log_v1_1_0, tools_weekly_log_v1_1_1, tools_weekly_log_v1_2_0 [INFERRED 0.85]
- **UI to Python Api bridge** — ui_index_api_bridge, ui_index_tick, speakon_api, requirements_pywebview [INFERRED 0.85]

## Communities (22 total, 6 thin omitted)

### Community 1 - "Api"
Cohesion: 0.07
Nodes (27): Edit dictation: Save & learn, Api, progress(), work(), clean(), pywebview JS-to-Python api bridge, bindSwitch(), boot() (+19 more)

### Community 2 - "SpeakOn"
Cohesion: 0.10
Nodes (5): foreground_app(), modifiers_down(), set_busy_priority(), SpeakOn, work()

### Community 3 - "engine.py"
Cohesion: 0.09
Nodes (16): combo_label(), hotkey_keys(), hotkey_label(), block_rms(), main(), run(), load_textproc(), main() (+8 more)

### Community 4 - "learn.py"
Cohesion: 0.10
Nodes (15): align(), apply_fixes(), diff_spans(), learn_fixes(), learn_from_wispr(), learn_lowercase(), learn_terms(), ngram_counts() (+7 more)

### Community 5 - "textproc.py"
Cohesion: 0.12
Nodes (18): apply_custom_words(), apply_replacements(), apply_spoken_commands(), _best_match(), collapse_stutters(), dictionary_warnings(), fix_midsentence_caps(), _keep_case() (+10 more)

### Community 6 - "SpeakOn"
Cohesion: 0.08
Nodes (33): Build-from-source agent prompt for Windows, history.json self-test check, Stand-alone SpeakOn.exe build (PyInstaller + build.ps1), Data folder C:\Users\<you>\SpeakOn, Dictionary rules (longest first, whole words, warnings), FluidVoice (Mac, GPL-3.0), Handy, Bottom-of-screen mic pill overlay (+25 more)

### Community 8 - "Hotkey Watcher"
Cohesion: 0.19
Nodes (3): HotkeyWatcher, key_name(), matches()

### Community 9 - "FlowBar"
Cohesion: 0.18
Nodes (5): BITMAPINFOHEADER, BLENDFUNCTION, FlowBar, _font(), WNDCLASS

### Community 10 - "Engine"
Cohesion: 0.14
Nodes (3): _Cancellable, Engine, is_english_only()

### Community 11 - "Microphone"
Cohesion: 0.21
Nodes (3): Microphone, v1.2.0 (mic kept ready with lead-in), TOGGLES settings list

### Community 12 - "Store"
Cohesion: 0.11
Nodes (3): load_json(), save_json(), Store

### Community 13 - "Learned"
Cohesion: 0.15
Nodes (3): entry_id(), fix_id(), Learned

### Community 15 - "graphify knowledge graph (graphify-out/)"
Cohesion: 0.50
Nodes (4): GRAPH_REPORT.md, graphify knowledge graph (graphify-out/), graphify query/path/explain commands, graphify update . (AST-only refresh)

### Community 18 - "corrections.py"
Cohesion: 0.24
Nodes (4): find_corrections(), _levenshtein(), looks_like_correction(), _words()

### Community 20 - "sendinput.py"
Cohesion: 0.29
Nodes (5): INPUT, KEYBDINPUT, MOUSEINPUT, type_text(), _U

### Community 21 - ".__init__"
Cohesion: 0.25
Nodes (4): main(), make_tone(), resource(), set_start_with_windows()

## Knowledge Gaps
- **14 isolated node(s):** `MOUSEINPUT`, `_U`, `INPUT`, `graphify query/path/explain commands`, `graphify update . (AST-only refresh)` (+9 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 136 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SpeakOn` connect `SpeakOn` to `speakon.py`, `Api`, `SpeakOn`, `Hotkey Watcher`, `FlowBar`, `Microphone`, `Store`, `EditWatcher`, `.__init__`?**
  _High betweenness centrality (0.168) - this node is a cross-community bridge._
- **Why does `Api` connect `Api` to `speakon.py`, `.__init__`, `SpeakOn`?**
  _High betweenness centrality (0.139) - this node is a cross-community bridge._
- **Why does `SpeakOn` connect `SpeakOn` to `Microphone`, `Api`, `SpeakOn`, `EditWatcher`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `SpeakOn` (e.g. with `SpeakOn` and `EditWatcher`) actually correct?**
  _`SpeakOn` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Api` (e.g. with `SpeakOn` and `pywebview JS-to-Python api bridge`) actually correct?**
  _`Api` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `HotkeyWatcher` (e.g. with `Push-to-talk Ctrl + Win (hold or tap)` and `SpeakOn`) actually correct?**
  _`HotkeyWatcher` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `MOUSEINPUT`, `_U`, `INPUT` to the rest of the system?**
  _14 weakly-connected nodes found - possible documentation gaps or missing edges._