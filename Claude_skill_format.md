Now let me build a comprehensive visual breakdown of the skill data format:Here's the expanded breakdown:

---

## SKILL.md format in detail

The YAML frontmatter has three fields. `name` is the skill's identifier and should match the folder name. `description` is the most critical field — it's the sole trigger mechanism, so it must describe both *what* the skill does and *when* to use it. It should be slightly "pushy" to prevent under-triggering. `compatibility` is optional and rarely used, listing required tools or dependencies.

The Markdown body follows standard conventions. Instructions should use the imperative form, explain the *why* behind things rather than just dictating rules, and prefer clear examples over rigid MUSTs. The target length is under 500 lines — if you're approaching that, add a layer of hierarchy with pointers to sub-files in `references/`.

---

## JSON data schemas

The skill ecosystem uses six distinct JSON file formats:

**evals.json** — defines test cases for the skill. Each eval has an `id`, a `prompt` (what the user would type), an `expected_output` description, optional `files` (relative paths to sample inputs), and `expectations` (verifiable string assertions like "The output includes X").

**eval_metadata.json** — one per test run directory. Mirrors the eval entry but also accumulates `assertions` as they're drafted during a run. The `eval_name` field should be descriptive, not just "eval-0".

**grading.json** — the grader agent's output per run. The `expectations` array uses exactly three fields: `text`, `passed`, and `evidence`. The `summary` block has pass/fail counts and a rate. Additional sections capture `execution_metrics`, `timing`, `claims` (extracted and verified factual claims from the output), `user_notes_summary` (uncertainties, workarounds), and optional `eval_feedback` (suggestions for improving the assertions themselves).

**metrics.json** — produced by the executor agent at `outputs/metrics.json`. Records tool call counts by type, total steps, files created, errors, and character counts for both output and transcript.

**timing.json** — wall clock data captured from the subagent task notification, which is the only place this data exists. Must be saved immediately. Fields include `total_tokens`, `duration_ms`, executor start/end timestamps, and grader start/end.

**benchmark.json** — the aggregated comparison across with-skill vs without-skill (or old vs new skill) runs. The `metadata` block captures the skill name, model, timestamp, and which evals were run. The `runs` array holds individual run results, each with `eval_id`, `eval_name`, `configuration` (must be exactly `"with_skill"` or `"without_skill"`), and a nested `result` object. The `run_summary` section computes mean ± stddev for pass rate, time, and tokens per configuration, plus a `delta`. The viewer reads all these field names exactly — deviating from the schema causes silent display failures.

Two additional schemas exist for the optional blind comparison feature: **comparison.json** (winner, reasoning, rubric scores, and expectation results for both A and B outputs) and **analysis.json** (post-hoc analysis of why one version beat another, with structured improvement suggestions).

---

## Workspace layout

During iteration, all outputs land in a sibling workspace directory:

```
skill-name-workspace/
├── history.json          ← version progression tracker
└── iteration-1/
    └── descriptive-name/ ← one dir per eval, named not numbered
        ├── eval_metadata.json
        ├── with_skill/
        │   ├── outputs/       ← files the skill produced
        │   ├── metrics.json
        │   └── timing.json
        └── without_skill/
            ├── outputs/
            ├── grading.json
            └── timing.json
```

**history.json** tracks version progression in improvement mode: each entry has a `version` (v0, v1...), a `parent` version it derives from, an `expectation_pass_rate`, a `grading_result` ("won", "lost", "tie", or "baseline"), and a flag for `is_current_best`.
