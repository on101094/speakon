# Graph Report - speakon  (2026-10-03)

## Corpus Check
- 26 files · ~21,208 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: (none) 3, .ico 1)

## Summary
- 489 nodes · 935 edges · 19 communities (15 shown, 4 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 68 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c854f7d6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- speakon.py
- Api
- SpeakOn
- engine.py
- learn.py
- textproc.py
- SpeakOn
- Dictation
- HotkeyWatcher
- FlowBar
- Engine
- Microphone
- Store
- Learned
- FakeMic
- graphify knowledge graph (graphify-out/)
- Cannot type into administrator apps
- test_api.py

## God Nodes (most connected - your core abstractions)
1. `SpeakOn` - 38 edges
2. `Store` - 33 edges
3. `Api` - 25 edges
4. `Dictation` - 19 edges
5. `HotkeyWatcher` - 19 edges
6. `pywebview JS-to-Python api bridge` - 19 edges
7. `SpeakOn` - 19 edges
8. `Learned` - 17 edges
9. `Microphone` - 17 edges
10. `entry_id()` - 13 edges

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

## Communities (19 total, 4 thin omitted)

### Community 0 - "speakon.py"
Cohesion: 0.07
Nodes (10): EditWatcher, find_corrections(), _levenshtein(), looks_like_correction(), _words(), foreground_app(), main(), make_tone() (+2 more)

### Community 1 - "Api"
Cohesion: 0.07
Nodes (27): Edit dictation: Save & learn, Api, progress(), work(), clean(), pywebview JS-to-Python api bridge, bindSwitch(), boot() (+19 more)

### Community 2 - "SpeakOn"
Cohesion: 0.10
Nodes (4): set_busy_priority(), set_start_with_windows(), SpeakOn, work()

### Community 3 - "engine.py"
Cohesion: 0.11
Nodes (13): block_rms(), main(), run(), load_textproc(), main(), wispr_texts(), align(), load() (+5 more)

### Community 4 - "learn.py"
Cohesion: 0.10
Nodes (15): align(), apply_fixes(), diff_spans(), learn_fixes(), learn_from_wispr(), learn_lowercase(), learn_terms(), ngram_counts() (+7 more)

### Community 5 - "textproc.py"
Cohesion: 0.12
Nodes (18): apply_custom_words(), apply_replacements(), apply_spoken_commands(), _best_match(), collapse_stutters(), dictionary_warnings(), fix_midsentence_caps(), _keep_case() (+10 more)

### Community 6 - "SpeakOn"
Cohesion: 0.07
Nodes (34): Build-from-source agent prompt for Windows, history.json self-test check, Stand-alone SpeakOn.exe build (PyInstaller + build.ps1), Data folder C:\Users\<you>\SpeakOn, Dictionary rules (longest first, whole words, warnings), FluidVoice (Mac, GPL-3.0), Handy, Bottom-of-screen mic pill overlay (+26 more)

### Community 8 - "HotkeyWatcher"
Cohesion: 0.10
Nodes (8): HotkeyWatcher, key_name(), matches(), INPUT, KEYBDINPUT, MOUSEINPUT, type_text(), _U

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
Cohesion: 0.08
Nodes (16): entry_id(), load_json(), save_json(), Store, test_add_dictionary_lines_skips_existing(), test_add_history_assigns_id_trims_and_saves(), test_concurrent_changes_lose_nothing(), guard() (+8 more)

### Community 13 - "Learned"
Cohesion: 0.11
Nodes (9): fix_id(), Learned, make(), test_apply_wispr(), test_concurrent_merges_lose_nothing(), test_entries_and_ids_survive_reordering(), test_lowercase_is_a_copy(), test_remove_term() (+1 more)

### Community 15 - "graphify knowledge graph (graphify-out/)"
Cohesion: 0.50
Nodes (4): GRAPH_REPORT.md, graphify knowledge graph (graphify-out/), graphify query/path/explain commands, graphify update . (AST-only refresh)

### Community 21 - "test_api.py"
Cohesion: 0.08
Nodes (7): combo_label(), hotkey_keys(), hotkey_label(), on_closing(), data_dir(), app(), test_dictionary_page()

## Knowledge Gaps
- **14 isolated node(s):** `MOUSEINPUT`, `_U`, `INPUT`, `graphify query/path/explain commands`, `graphify update . (AST-only refresh)` (+9 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 150 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SpeakOn` connect `SpeakOn` to `speakon.py`, `Api`, `SpeakOn`, `HotkeyWatcher`, `FlowBar`, `Microphone`, `Store`?**
  _High betweenness centrality (0.158) - this node is a cross-community bridge._
- **Why does `Api` connect `Api` to `speakon.py`, `SpeakOn`?**
  _High betweenness centrality (0.129) - this node is a cross-community bridge._
- **Why does `Store` connect `Store` to `speakon.py`, `SpeakOn`, `test_api.py`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `SpeakOn` (e.g. with `SpeakOn` and `EditWatcher`) actually correct?**
  _`SpeakOn` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Api` (e.g. with `SpeakOn` and `pywebview JS-to-Python api bridge`) actually correct?**
  _`Api` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `HotkeyWatcher` (e.g. with `Push-to-talk Ctrl + Win (hold or tap)` and `SpeakOn`) actually correct?**
  _`HotkeyWatcher` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `MOUSEINPUT`, `_U`, `INPUT` to the rest of the system?**
  _14 weakly-connected nodes found - possible documentation gaps or missing edges._