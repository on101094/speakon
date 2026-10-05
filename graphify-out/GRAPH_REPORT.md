# Graph Report - speakon  (2026-10-05)

## Corpus Check
- 33 files · ~25,709 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: (none) 3, .ico 1)

## Summary
- 571 nodes · 1103 edges · 28 communities (17 shown, 11 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 69 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `571227f8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- corrections.py
- Api
- SpeakOn
- engine.py
- learn.py
- textproc.py
- SpeakOn
- Dictation
- HotkeyWatcher
- overlay.py
- test_engine.py
- Microphone
- Store
- Learned
- speakon.py
- graphify knowledge graph (graphify-out/)
- Cannot type into administrator apps
- entry_id
- sendinput.py
- store.py
- test_api.py
- FakeMic
- .save_history
- FlowBar
- app

## God Nodes (most connected - your core abstractions)
1. `SpeakOn` - 38 edges
2. `Store` - 34 edges
3. `Dictation` - 25 edges
4. `Api` - 25 edges
5. `HotkeyWatcher` - 19 edges
6. `pywebview JS-to-Python api bridge` - 19 edges
7. `SpeakOn` - 19 edges
8. `Microphone` - 18 edges
9. `Learned` - 17 edges
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
- **Reducing dictation wait under CPU load** — tools_weekly_log_v1_2_1, tools_weekly_log_v1_2_2, ui_index_adaptive_polling, ui_index_tick, speakon_set_busy_priority, tools_weekly_log_real_median_wait [INFERRED 0.85]
- **Sound-alike snapping of dictionary words** — textproc_apply_custom_words, textproc_best_match, textproc_swallows_small_word, tools_weekly_log_sound_alike_snapping [INFERRED 0.85]
- **SpeakOn voice-learning mechanisms** — readme_learn_from_wispr, readme_fix_after_dictating, readme_save_and_learn, learn_learn_fixes, corrections_editwatcher [INFERRED 0.85]
- **Low-latency dictation pipeline** — readme_transcribe_while_talking, readme_mic_lead_in, tools_weekly_log_v1_1_0, tools_weekly_log_v1_1_1, tools_weekly_log_v1_2_0 [INFERRED 0.85]
- **UI to Python Api bridge** — ui_index_api_bridge, ui_index_tick, speakon_api, requirements_pywebview [INFERRED 0.85]

## Communities (28 total, 11 thin omitted)

### Community 0 - "corrections.py"
Cohesion: 0.17
Nodes (3): EditWatcher, find_corrections(), _words()

### Community 1 - "Api"
Cohesion: 0.07
Nodes (27): Edit dictation: Save & learn, Api, progress(), work(), clean(), pywebview JS-to-Python api bridge, bindSwitch(), boot() (+19 more)

### Community 2 - "SpeakOn"
Cohesion: 0.10
Nodes (5): foreground_app(), set_busy_priority(), set_start_with_windows(), SpeakOn, work()

### Community 3 - "engine.py"
Cohesion: 0.09
Nodes (20): block_rms(), main(), run(), load_textproc(), main(), wispr_texts(), align(), load() (+12 more)

### Community 4 - "learn.py"
Cohesion: 0.07
Nodes (27): align(), apply_fixes(), diff_spans(), learn_fixes(), learn_from_wispr(), learn_lowercase(), learn_terms(), ngram_counts() (+19 more)

### Community 5 - "textproc.py"
Cohesion: 0.08
Nodes (28): looks_like_correction(), clean(), test_filler_before_a_full_stop_keeps_the_sentence_break(), test_filler_cleanup_otherwise_unchanged(), test_fixes_report_only_rules_that_matched_the_spoken_text(), test_learned_lowercase_words_undo_a_capital_after_a_pause(), test_many_rules_keep_their_placeholders_apart(), test_shorter_rule_does_not_rewrite_a_longer_rules_output() (+20 more)

### Community 6 - "SpeakOn"
Cohesion: 0.07
Nodes (28): Engine, is_english_only(), Build-from-source agent prompt for Windows, history.json self-test check, Stand-alone SpeakOn.exe build (PyInstaller + build.ps1), Data folder C:\Users\<you>\SpeakOn, Dictionary rules (longest first, whole words, warnings), FluidVoice (Mac, GPL-3.0) (+20 more)

### Community 8 - "HotkeyWatcher"
Cohesion: 0.19
Nodes (3): HotkeyWatcher, key_name(), matches()

### Community 9 - "overlay.py"
Cohesion: 0.24
Nodes (4): BITMAPINFOHEADER, BLENDFUNCTION, _font(), WNDCLASS

### Community 10 - "test_engine.py"
Cohesion: 0.10
Nodes (15): _Cancellable, fake_onnxruntime(), FakeEngine, FakeRunOptions, FakeSession, previewed(), run_in_thread(), talk() (+7 more)

### Community 11 - "Microphone"
Cohesion: 0.11
Nodes (5): Microphone, FakeStream, test_warm_and_begin_at_the_same_time_open_one_stream(), v1.2.0 (mic kept ready with lead-in), TOGGLES settings list

### Community 12 - "Store"
Cohesion: 0.25
Nodes (12): Store, test_add_dictionary_lines_skips_existing(), test_add_history_assigns_id_trims_and_saves(), test_construction_does_not_write_settings(), test_dictionary_entries_by_id(), test_history_actions_find_the_entry_after_the_list_shifts(), test_history_actions_on_missing_entry_are_no_ops(), test_load_backfills_ids_and_resets_unknown_hotkey() (+4 more)

### Community 14 - "speakon.py"
Cohesion: 0.12
Nodes (4): main(), make_tone(), modifiers_down(), resource()

### Community 15 - "graphify knowledge graph (graphify-out/)"
Cohesion: 0.50
Nodes (4): GRAPH_REPORT.md, graphify knowledge graph (graphify-out/), graphify query/path/explain commands, graphify update . (AST-only refresh)

### Community 18 - "entry_id"
Cohesion: 0.18
Nodes (4): entry_id(), fix_id(), test_concurrent_changes_lose_nothing(), guard()

### Community 19 - "sendinput.py"
Cohesion: 0.29
Nodes (5): INPUT, KEYBDINPUT, MOUSEINPUT, type_text(), _U

### Community 21 - "test_api.py"
Cohesion: 0.05
Nodes (15): combo_label(), hotkey_keys(), hotkey_label(), data_dir(), test_dictionary_page(), load(), main(), old_finish() (+7 more)

## Knowledge Gaps
- **14 isolated node(s):** `MOUSEINPUT`, `_U`, `INPUT`, `graphify query/path/explain commands`, `graphify update . (AST-only refresh)` (+9 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 179 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SpeakOn` connect `SpeakOn` to `corrections.py`, `Api`, `SpeakOn`, `HotkeyWatcher`, `Microphone`, `Store`, `speakon.py`, `FlowBar`?**
  _High betweenness centrality (0.134) - this node is a cross-community bridge._
- **Why does `Api` connect `Api` to `SpeakOn`, `speakon.py`?**
  _High betweenness centrality (0.116) - this node is a cross-community bridge._
- **Why does `Store` connect `Store` to `SpeakOn`, `speakon.py`, `entry_id`, `store.py`, `.set_dictionary`, `.save_history`, `app`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `SpeakOn` (e.g. with `SpeakOn` and `EditWatcher`) actually correct?**
  _`SpeakOn` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Api` (e.g. with `SpeakOn` and `pywebview JS-to-Python api bridge`) actually correct?**
  _`Api` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `HotkeyWatcher` (e.g. with `Push-to-talk Ctrl + Win (hold or tap)` and `SpeakOn`) actually correct?**
  _`HotkeyWatcher` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `MOUSEINPUT`, `_U`, `INPUT` to the rest of the system?**
  _14 weakly-connected nodes found - possible documentation gaps or missing edges._