# autoresearch-gear

This is an experiment to have the LLM do its own research. You do this by using genetic algorithms for search.

The search policy is externalized into `gear.py`. You may not modify `gear.py`. `gear.py` is the source of truth for suggestions and bookkeeping at any given moment.

## Setup

To set up a new experiment, work with the user to:

1. **Agree on a run tag**: propose a tag based on today's date, e.g. `apr12-gear1`. The branch `autoresearch/<tag>` must not already exist — this is a fresh run.
2. **Create the branch**: `git checkout -b autoresearch/<tag>` from current master.
3. **Read the in-scope files**: The repo is small. Read these files for full context:
   - `README.md` — repository context.
   - `prepare.py` — fixed constants, data prep, tokenizer, dataloader, evaluation. Do not modify.
   - `train.py` — the file you modify for model experiments.
   - `gear.py` — the fixed external controller. Read it carefully; do not modify it.
4. **Verify data exists**: Check that `~/.cache/autoresearch/` contains data shards and a tokenizer. If not, tell the human to run `uv run prepare.py`.
5. **Initialize controller bookkeeping**: Run:
   - `python gear.py init --run-tag <tag>`
6. **Confirm the controller files exist**: These should now exist:
   - `gear_state.json`
   - `results.tsv`
   - `frontier.tsv`
   - `controller_events.tsv`
   - `logs/`
   - `reflections/`
7. **Confirm and go**: Confirm setup looks good.

Once you get confirmation, kick off the experimentation.

## Experimentation

Each experiment runs on a single GPU. The training script runs for a fixed time budget of 5 minutes (wall clock training time, excluding startup/compilation). You launch it simply as: `uv run train.py`.

What you CAN do:

- Modify `train.py` — this is the main file you edit for model experiments.
- Write reflection files under `reflections/`.
- Read the bookkeeping files created by `gear.py`.
- Move the working branch around by resetting it to controller-chosen parent commits/tags.

What you CANNOT do:

- Modify `prepare.py`. It is read-only. It contains the fixed evaluation, data loading, tokenizer, and training constants.
- Modify `gear.py`. It is read-only.
- Install new packages or add dependencies. You can only use what's already in `pyproject.toml`.
- Modify the evaluation harness. The `evaluate_bpb` function in `prepare.py` is the ground truth metric.
- Manually override frontier or promotion decisions outside `gear.py`.
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

**You may not override, reinterpret, or "deviate from" the suggestion under any circumstances.** Even if you believe the suggestion is suboptimal — a degenerate crossover, a known-bad parent, a redundant experiment — you must execute it faithfully. The search policy lives in `gear.py`, not in your judgment. Your role is to execute the suggestion with the best possible `train.py` edit, not to second-guess which parent or operator to use.

**Crossovers in particular must be respected.** When the suggestion says `crossover`, you must:

1. Reset to the `parent1` commit as your base.
2. Inspect `parent2` (check out the commit, read its `train.py`, diff it against parent1) to understand what idea it carries.
3. Transplant exactly one coherent idea from `parent2` into the `parent1` base.

You do not get to reclassify a crossover as a mutation, skip the second parent, or substitute a different donor. The whole point of crossover is combining proven ideas from different lineages — if you refuse to do it, the genetic search degenerates into hill-climbing.

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

Do not write `results.tsv` or `frontier.tsv` by hand. `gear.py` owns them.

The controller writes `results.tsv` with these columns:

```text
exp_id	commit	parent1	parent2	val_bpb	memory_gb	params_m	status	mutation_kind	description	controller_sha	promoted_slot
```

Note: `parent1` and `parent2` are **commit hashes**, not elite slot names. This makes parentage unambiguous even after elite slots get replaced. The `promoted_slot` column still records the elite tag for the frontier mechanism.

The controller writes `frontier.tsv` with the current active pool and branch statistics.

`controller_events.tsv` records controller-side events such as promotions and discards.

You may read these files freely, but do not edit the TSV files manually.

## Committing artifacts

Everything the run produces must end up in git. Nothing is allowed to stay untracked. This applies to all of: `logs/*.log`, `reflections/*.md`, `results.tsv`, `frontier.tsv`, `controller_events.tsv`, and `gear_state.json`.

Concretely:

- After every experiment step, stage and commit all artifacts produced by that step (see step 14 in the experiment-step protocol).
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

## Experiment step

Follow this loop:

1. Look at the git state: the current branch/commit and the current controller state.
2. Run `python gear.py status` to see the upcoming `exp_id`, frontier, and controller SHA.
3. Run `python gear.py suggest`.
4. **The suggestion is binding.** Use it as the source of truth:
   - `baseline`: run the untouched `train.py`
   - `mutate`: reset to `parent1` commit and create one coherent child from it
   - `crossover`: reset to `parent1` commit as the base and intentionally transplant one coherent idea from `parent2` commit
5. Read the suggestion's `parent1_tag` (elite slot tag) and `parent1` (commit hash). Materialize the parent state:
   - `git switch autoresearch/<tag>`
   - `git reset --hard <parent1_tag>` (use the tag for convenience; the commit hash is the authoritative reference)
   - For crossover, also inspect `parent2` by reading the diff or checking out the commit to understand what idea to transplant.
6. Tune `train.py` with one experimental idea by directly hacking the code.
7. `git commit` the train.py change.
8. Run the experiment: `uv run train.py > logs/<exp_id>.log 2>&1`
9. Read out the results: `grep "^val_bpb:\|^peak_vram_mb:\|^num_params_M:" logs/<exp_id>.log`
10. If the grep output is empty, the run crashed. Run `tail -n 50 logs/<exp_id>.log` to read the stack trace and attempt a fix. If you cannot get things to work after more than a few attempts, give up.
11. Write the reflection in `reflections/<exp_id>.md`.
12. Record the run through the controller, using **commit hashes** for parents:
    - success:
      - `python gear.py record-run --exp-id <exp_id> --parent1 <parent1_commit> --parent2 <parent2_commit> --mutation-kind <baseline|mutate|crossover> --description "<short description>" --status ok --val-bpb <VAL> --memory-gb <GB> --params-m <PARAMS> --apply-git`
    - crash:
      - `python gear.py record-run --exp-id <exp_id> --parent1 <parent1_commit> --parent2 <parent2_commit> --mutation-kind <baseline|mutate|crossover> --description "<short description>" --status crash --apply-git`
    - Note: `--parent1` and `--parent2` must be the commit hashes from the suggestion, not elite slot names. Use `-` for parent2 when there is no second parent.
13. Commit all artifacts produced by this step:
    - `git add logs/<exp_id>.log reflections/<exp_id>.md results.tsv frontier.tsv controller_events.tsv gear_state.json`
    - `git commit -m "exp <exp_id>: artifacts"` (skip if `git status` shows nothing staged)
14. Verify nothing is left untracked: `git status` should be clean under the artifact paths.

## The experiment loop

The experiment runs on a dedicated branch (e.g. `autoresearch/apr12-gear1`).

LOOP FOREVER:

1. Read the current controller state and recent search memory.
2. Follow the experiment-step protocol above. **Follow the suggestion exactly.**

Timeout: Each experiment should take ~5 minutes total (+ a few seconds for startup and eval overhead). If a run exceeds 10 minutes, kill it and treat it as a failure.

Crashes: If a run crashes (OOM, or a bug, or etc.), use your judgment. If it is something dumb and easy to fix, fix it and re-run. If the idea itself is fundamentally broken, just log `crash` through the controller and move on.

NEVER STOP: Once the experiment loop has begun (after the initial setup), do NOT pause to ask the human if you should continue. Do NOT ask "should I keep going?" or "is this a good stopping point?". The human might be asleep or away from the computer and expects you to continue working indefinitely until manually stopped. You are autonomous.

If you run out of ideas, think harder — re-read the in-scope files, re-read `frontier.tsv`, re-read reflections, combine previous near-misses, and try more radical but still coherent changes. The loop runs until the human interrupts you, period.

## Important reminders

- Only edit `train.py` for model experiments.
- Never edit `prepare.py`.
- Never edit `gear.py`.
- Never change the evaluation harness.
- **Never deviate from `gear.py suggest` output.** The operator, parent1, and parent2 are not negotiable.
- **Always execute crossovers faithfully.** Inspect parent2, identify its idea, transplant it into parent1. Do not downgrade crossovers to mutations.
- Maintain `results.tsv`, `frontier.tsv`, `controller_events.tsv`, `logs/`, `reflections/`, and `gear_state.json`.
- Commit every artifact every step. Nothing untracked.
- Use the working branch as a movable workspace.
- Let `gear.py` own frontier selection and promotion.
- Prefer semantic crossover, not raw textual merges.
- Be clear in your descriptions. The bookkeeping files are your memory.
- Parents in `results.tsv` are commit hashes, not elite slot names. Use the commit hash from the suggestion.