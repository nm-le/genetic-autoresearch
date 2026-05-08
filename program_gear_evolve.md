# autoresearch-gear

This is an experiment to have the LLM do its own research. You do this by using genetic algorithms for search.

The starting search policy is externalized into `gear.py`. You may improve `gear.py`, but only under strict logging and reproducibility rules. `gear.py` is the source of truth for suggestions and bookkeeping at any given moment.

**Controller-improvement steps are not optional flavor — they are half the point of this variant.** If you only ever edit `train.py`, you are running the non-self-modifying version of this experiment. Explicitly consider controller changes; do not silently default to experiment steps forever.

## Setup

To set up a new experiment, work with the user to:

1. **Agree on a run tag**: propose a tag based on today's date, e.g. `apr12-gear2`. The branch `autoresearch/<tag>` must not already exist — this is a fresh run.
2. **Create the branch**: `git checkout -b autoresearch/<tag>` from current master.
3. **Read the in-scope files**: The repo is small. Read these files for full context:
   - `README.md` — repository context.
   - `prepare.py` — fixed constants, data prep, tokenizer, dataloader, evaluation. Do not modify.
   - `train.py` — the file you modify for model experiments.
   - `gear.py` — the starting external controller. Read it carefully before changing anything.
4. **Verify data exists**: Check that `~/.cache/autoresearch/` contains data shards and a tokenizer. If not, tell the human to run `uv run prepare.py`.
5. **Initialize controller bookkeeping**: Run:
   - `python gear.py init --run-tag <tag>`
6. **Initialize controller memory**: Create `controller_journal.md` if it does not already exist.
7. **Initialize decision log**: Create `decisions.md` if it does not already exist, with a header line like `# Decision log — <tag>`.
8. **Confirm the controller files exist**: These should now exist:
   - `gear_state.json`
   - `results.tsv`
   - `frontier.tsv`
   - `controller_events.tsv`
   - `logs/`
   - `reflections/`
   - `controller_journal.md`
   - `decisions.md`
9. **Confirm and go**: Confirm setup looks good.

Once you get confirmation, kick off the experimentation.

## Experimentation

Each experiment runs on a single GPU. The training script runs for a fixed time budget of 5 minutes (wall clock training time, excluding startup/compilation). You launch it simply as: `uv run train.py`.

What you CAN do:

- Modify `train.py` — this is the main file you edit for model experiments.
- Modify `gear.py` — but only as an explicit controller-improvement step with full logging.
- Write reflection files under `reflections/`.
- Write controller-change notes in `controller_journal.md`.
- Append decision lines to `decisions.md`.
- Read the bookkeeping files created by `gear.py`.
- Move the working branch around by resetting it to controller-chosen parent commits/tags.

What you CANNOT do:

- Modify `prepare.py`. It is read-only. It contains the fixed evaluation, data loading, tokenizer, and training constants.
- Install new packages or add dependencies. You can only use what's already in `pyproject.toml`.
- Modify the evaluation harness. The `evaluate_bpb` function in `prepare.py` is the ground truth metric.
- Manually override frontier or promotion decisions outside the currently checked-in `gear.py`.
- **Deviate from a `gear.py suggest` output.** See the Binding suggestions rule below.

The goal is simple: get the lowest val_bpb. Since the time budget is fixed, you do not need to optimize runtime beyond making sure the run finishes and does not crash.

VRAM is a soft constraint. Some increase is acceptable for meaningful val_bpb gains, but it should not blow up dramatically.

Simplicity criterion: All else being equal, simpler is better. A small improvement that adds ugly complexity is not worth it. Conversely, removing something and getting equal or better results is a great outcome. A 0.001 val_bpb improvement that adds 20 lines of hacky code? Probably not worth it. A 0.001 val_bpb improvement from deleting code? Definitely keep. An improvement of ~0 but much simpler code? Keep.

The first run: Your very first run should always be to establish the baseline, so you will run the training script as is.

## Binding suggestions rule

**The output of `python gear.py suggest` is binding.** You must follow the operator, parent1, and parent2 exactly as given. This is the central contract of the externalized-controller design: `gear.py` owns the search policy, and you execute it.

Specifically:

- If `gear.py` says `operator: mutate`, you mutate. You do not crossover.
- If `gear.py` says `operator: crossover`, you crossover. You do not mutate.
- If `gear.py` says `parent1: <commit>`, you reset to that commit. You do not pick a different parent.
- If `gear.py` says `parent2: <commit>`, you transplant an idea from that commit. You do not substitute a different donor.

**If you believe a suggestion is bad** — degenerate crossover, known-bad parent, redundant experiment — **the correct response is NOT to deviate.** It is to:

1. Abort the experiment step.
2. Switch to a controller-improvement step.
3. Fix `gear.py` so it produces better suggestions.
4. Re-run `python gear.py suggest` and follow the new output.

Deviating from the suggestion while leaving `gear.py` unchanged defeats the entire purpose of externalizing the search policy. The search policy lives in `gear.py`, not in your head. If the policy is wrong, fix the policy.

**Any deviation from the suggestion is a controller bug, and must be treated as one.**

## Output format

Once the script finishes it prints a summary like this:

```text
---
val_bpb:          0.997900
training_seconds: 300.1
total_seconds:    325.9
peak_vram_mb:     45060.2
mfu_percent:      39.80
total_tokens_M:   499.6
num_steps:        953
num_params_M:     50.3
depth:            8
```

You can extract the key metrics from the log file:

```bash
grep "^val_bpb:\|^peak_vram_mb:\|^num_params_M:" logs/<exp_id>.log
```

If the grep output is empty, the run crashed. Read the Python stack trace:

```bash
tail -n 50 logs/<exp_id>.log
```

## Logging results

Do not write `results.tsv` or `frontier.tsv` by hand. The current version of `gear.py` owns them.

The controller writes `results.tsv` with these columns:

```text
exp_id	commit	parent1	parent2	val_bpb	memory_gb	params_m	status	mutation_kind	description	controller_sha	promoted_slot
```

Note: `parent1` and `parent2` are **commit hashes**, not elite slot names. This makes parentage unambiguous even after elite slots get replaced. The `promoted_slot` column still records the elite tag for the frontier mechanism.

The controller writes `frontier.tsv` with the current active pool and branch statistics.

`controller_events.tsv` records controller-side events such as promotions and discards.

`controller_journal.md` is the human-readable memory of why `gear.py` changed.

`decisions.md` is the per-iteration record of the meta-decision (experiment vs. controller step) — see the Decision log section below.

You may read these files freely, but do not edit the TSV files manually.

## Committing artifacts

Everything the run produces must end up in git. Nothing is allowed to stay untracked. This applies to all of: `logs/*.log`, `reflections/*.md`, `results.tsv`, `frontier.tsv`, `controller_events.tsv`, `gear_state.json`, `controller_journal.md`, and `decisions.md`.

Concretely:

- After every experiment step, stage and commit all artifacts produced by that step (see step 15 in the experiment-step protocol).
- After every controller-improvement step, commit the journal update and any bookkeeping files touched by the controller change (see the controller protocol).
- If `git status` ever shows untracked or modified files under the artifact paths above, commit them before moving on.

## Reflections

For every experiment, write a short reflection file under `reflections/`, e.g. `reflections/exp0007.md`.

Keep it short, structured, and numerical. Prefer exact values and deltas over vague words.

Each reflection should record:

- parent1 (commit hash)
- parent2 (commit hash, or `-`)
- operator
- what changed
- parent metrics if known
- child metrics
- deltas
- decision summary
- whether and when the idea should be revisited
- which prior experiment it is closest to

## Decision log

Before every loop iteration — whether it will be an experiment step or a controller-improvement step — append exactly one line to `decisions.md` in this format:

```text
<ISO timestamp> | next exp_id: <id> | choice: <experiment|controller> | reason: <one sentence>
```

Rules:

- If `choice: experiment`, the reason must explicitly state whether you considered a controller step and why you rejected it. Examples:
  - `reason: considered controller step; rejected because last 3 experiments each improved val_bpb (search healthy)`
  - `reason: considered controller step; rejected because only 4 experiments since last controller change (too early to re-assess)`
  - `reason: did not consider controller step — this is one of the first 5 experiments, need baseline signal first`
- If `choice: controller`, the reason must name the specific pathology being fixed (e.g. "frontier collapsed to one branch", "same mutation suggested 4 times in a row", "crossover never tried despite 2+ viable parents").
- If you have done **5 or more experiment steps in a row without a controller-improvement step**, the next iteration's decision line must either be `choice: controller`, OR contain an explicit justification in the reason field of why the search is still healthy and no policy change is warranted. You may not silently run a 6th, 7th, 8th consecutive experiment step without writing down that justification.

The decision log exists so that when a run ends with `gear.py` untouched, the reader can reconstruct *why* — and so that the model is forced, every iteration, to at least consider the controller level.

## Two kinds of steps

At each outer-loop step, choose one of two actions:

### 1. Experiment step
Use the current `gear.py` to choose and evaluate a child in `train.py`.

### 2. Controller-improvement step
Modify `gear.py` itself to improve search behavior.

Controller-improvement steps should be relatively rare, but they are a first-class part of this variant. A good default is at most 1 controller-improvement step in any block of 5 completed steps, and only when the recent search appears stuck, repetitive, or poorly calibrated. "Stuck" includes: frontier not changing, same operator/parent pair recurring, crossovers never being suggested, or suggestions that ignore obviously promising children.

## Experiment step

Follow this loop:

1. Append the decision line to `decisions.md` (see Decision log above).
2. Look at the git state: the current branch/commit and the current controller state.
3. Run `python gear.py status` to see the upcoming `exp_id`, frontier, and controller SHA.
4. Run `python gear.py suggest`.
5. **The suggestion is binding.** Use it as the source of truth:
   - `baseline`: run the untouched `train.py`
   - `mutate`: reset to `parent1` commit and create one coherent child from it
   - `crossover`: reset to `parent1` commit as the base and intentionally transplant one coherent idea from `parent2` commit
   - If you believe the suggestion is bad, **do not deviate** — abort this experiment step and switch to a controller-improvement step to fix `gear.py`, then re-suggest.
6. Read the suggestion's `parent1_tag` (elite slot tag) and `parent1` (commit hash). Materialize the parent state:
   - `git switch autoresearch/<tag>`
   - `git reset --hard <parent1_tag>` (use the tag for convenience; the commit hash is the authoritative reference)
   - For crossover, also inspect `parent2` by reading the diff or checking out the commit to understand what idea to transplant.
7. Tune `train.py` with one experimental idea by directly hacking the code.
8. `git commit` the train.py change.
9. Run the experiment: `uv run train.py > logs/<exp_id>.log 2>&1`
10. Read out the results: `grep "^val_bpb:\|^peak_vram_mb:\|^num_params_M:" logs/<exp_id>.log`
11. If the grep output is empty, the run crashed. Run `tail -n 50 logs/<exp_id>.log` to read the stack trace and attempt a fix. If you cannot get things to work after more than a few attempts, give up.
12. Write the reflection in `reflections/<exp_id>.md`.
13. Record the run through the current controller, using **commit hashes** for parents:
    - success:
      - `python gear.py record-run --exp-id <exp_id> --parent1 <parent1_commit> --parent2 <parent2_commit> --mutation-kind <baseline|mutate|crossover> --description "<short description>" --status ok --val-bpb <VAL> --memory-gb <GB> --params-m <PARAMS> --apply-git`
    - crash:
      - `python gear.py record-run --exp-id <exp_id> --parent1 <parent1_commit> --parent2 <parent2_commit> --mutation-kind <baseline|mutate|crossover> --description "<short description>" --status crash --apply-git`
    - Note: `--parent1` and `--parent2` must be the commit hashes from the suggestion, not elite slot names. Use `-` for parent2 when there is no second parent.
14. Commit all artifacts produced by this step:
    - `git add logs/<exp_id>.log reflections/<exp_id>.md results.tsv frontier.tsv controller_events.tsv gear_state.json decisions.md`
    - `git commit -m "exp <exp_id>: artifacts"` (skip if `git status` shows nothing staged)
15. Verify nothing is left untracked: `git status` should be clean under the artifact paths.

## Controller-improvement step

A controller change is allowed only if you log it.

1. Append the decision line to `decisions.md` with `choice: controller` and a reason naming the pathology.
2. Before editing `gear.py`, append a short entry to `controller_journal.md` with:
   - current controller SHA from `python gear.py status`
   - the problem you are trying to fix
   - the planned change
   - the expected effect
3. Edit `gear.py`.
4. Sanity check it:
   - `python -m py_compile gear.py`
5. Commit the controller change separately from model changes:
   - `git add gear.py`
   - `git commit -m "controller: <short description>"`
6. Append another short note to `controller_journal.md` with:
   - what actually changed
   - whether the file compiled
   - what search behavior should now change
7. Commit the journal and decision-log updates:
   - `git add controller_journal.md decisions.md`
   - `git commit -m "controller: journal note"`

Important rule: a controller change does not count as success by itself. Its value is measured only through subsequent experiment suggestions and outcomes.

## The experiment loop

The experiment runs on a dedicated branch (e.g. `autoresearch/apr12-gear2`).

LOOP FOREVER:

1. Append the decision line to `decisions.md`.
2. Read the current controller state and recent search memory (including the last ~10 lines of `decisions.md` and the tail of `controller_journal.md`).
3. Decide whether the next step is an experiment step or a controller-improvement step, applying the 5-in-a-row rule from the Decision log section.
4. If it is an experiment step, follow the experiment-step protocol above. **Follow the suggestion exactly.** If the suggestion looks wrong, switch to step 5 instead.
5. If it is a controller-improvement step, follow the controller-improvement protocol above, then continue with experiments.

Timeout: Each experiment should take ~5 minutes total (+ a few seconds for startup and eval overhead). If a run exceeds 10 minutes, kill it and treat it as a failure.

Crashes: If a run crashes (OOM, or a bug, or etc.), use your judgment. If it is something dumb and easy to fix, fix it and re-run. If the idea itself is fundamentally broken, just log `crash` through the controller and move on.

NEVER STOP: Once the experiment loop has begun (after the initial setup), do NOT pause to ask the human if you should continue. Do NOT ask "should I keep going?" or "is this a good stopping point?". The human might be asleep or away from the computer and expects you to continue working indefinitely until manually stopped. You are autonomous.

If you run out of ideas, think harder — re-read the in-scope files, re-read `frontier.tsv`, re-read reflections, inspect `controller_journal.md`, inspect `decisions.md` for patterns in your own meta-choices, combine previous near-misses, and only then consider adjusting `gear.py`.

## Important reminders

- Only edit `train.py` for model experiments.
- Never edit `prepare.py`.
- Only edit `gear.py` as an explicit controller-improvement step with logging.
- Never change the evaluation harness.
- **Never deviate from `gear.py suggest` output.** If the suggestion is bad, fix `gear.py`.
- Maintain `results.tsv`, `frontier.tsv`, `controller_events.tsv`, `logs/`, `reflections/`, `gear_state.json`, `controller_journal.md`, and `decisions.md`.
- Commit every artifact every step. Nothing untracked.
- Every loop iteration must produce exactly one line in `decisions.md` before anything else happens.
- Use the working branch as a movable workspace.
- Let the current `gear.py` own frontier selection and promotion.
- Prefer semantic crossover, not raw textual merges.
- Be clear in your descriptions. The bookkeeping files are your memory.
- Controller-improvement steps are half the point of this variant. Do not forget they exist.
- Parents in `results.tsv` are commit hashes, not elite slot names. Use the commit hash from the suggestion.