# autoresearch-genetic

This is an experiment to have the LLM do its own research.

## Setup

To set up a new experiment, work with the user to:

1. **Agree on a run tag**: propose a tag for a fresh run, e.g. `apr10-gen1`. The branch `autoresearch/<tag>` must not already exist — this is a fresh run.
2. **Create the branch**: `git checkout -b autoresearch/<tag>` from current master.
3. **Read the in-scope files**: The repo is small. Read these files for full context:
   - `README.md` — repository context.
   - `prepare.py` — fixed constants, data prep, tokenizer, dataloader, evaluation. Do not modify.
   - `train.py` — the file you modify. Model architecture, optimizer, training loop.
4. **Verify data exists**: Check that `~/.cache/autoresearch/` contains data shards and a tokenizer. If not, tell the human to run `uv run prepare.py`.
5. **Initialize the bookkeeping files**: Create these files if they do not already exist:
   - `results.tsv`
   - `population.tsv`
6. **Initialize the bookkeeping directories**: Create these directories if they do not already exist:
   - `logs/`
   - `reflections/`
7. **Initialize elite tags**: Do not create any elite tags yet. The baseline run will create the first elite.
8. **Confirm and go**: Confirm setup looks good.

Once you get confirmation, kick off the experimentation.

## Experimentation

Each experiment runs on a single GPU. The training script runs for a **fixed time budget of 5 minutes** (wall clock training time, excluding startup/compilation). You launch it simply as: `uv run train.py`.

**What you CAN do:**

- Modify `train.py` — this is the only file you edit. Everything is fair game: model architecture, optimizer, hyperparameters, training loop, batch size, model size, etc.
- Move the working branch around by resetting it to elite commits.
- Maintain a small elite population using git tags and the bookkeeping files.

**What you CANNOT do:**

- Modify `prepare.py`. It is read-only. It contains the fixed evaluation, data loading, tokenizer, and training constants.
- Install new packages or add dependencies. You can only use what's already in `pyproject.toml`.
- Modify the evaluation harness. The `evaluate_bpb` function in `prepare.py` is the ground truth metric.

**The goal is simple: get the lowest val_bpb.** Since the time budget is fixed, you do not need to optimize runtime beyond making sure the run finishes and does not crash.

**VRAM** is a soft constraint. Some increase is acceptable for meaningful val_bpb gains, but it should not blow up dramatically.

**Simplicity criterion**: All else being equal, simpler is better. A small improvement that adds ugly complexity is not worth it. Conversely, removing something and getting equal or better results is a great outcome. A 0.001 val_bpb improvement that adds 20 lines of hacky code? Probably not worth it. A 0.001 val_bpb improvement from deleting code? Definitely keep. An improvement of ~0 but much simpler code? Keep.

## Population

Maintain a population of at most **P = 4** elites.

The population lives in two places:

1. **git tags** — the durable pointers to elite commits:

   - `elite/0`
   - `elite/1`
   - `elite/2`
   - `elite/3`

2. **population.tsv** — the readable summary of the current elite pool.

The working branch (for example `autoresearch/apr10-gen1`) is **not** the population. It is only the current workspace where you spawn children. The branch can move around freely. The elite tags preserve the population.

Try to preserve these roles:

- one `best`
- one `lean`
- one or two `diverse`

Example:

- `elite/0` = best overall
- `elite/1` = lower-memory candidate
- `elite/2` = optimizer direction
- `elite/3` = architecture direction

## The first run

Your very first run should always establish the baseline.

Procedure:

1. Stay on the working branch, e.g. `autoresearch/<tag>`.
2. Run the training script as is:
   - `uv run train.py > logs/exp0001.log 2>&1`
3. Read out the results:
   - `grep "^val_bpb:\|^peak_vram_mb:\|^num_params_M:" logs/exp0001.log`
4. Commit the baseline code if needed.
5. Create the first elite tag:
   - `git tag elite/0 HEAD`
6. Record the baseline in both `results.tsv` and `population.tsv`.

At this point the population contains exactly one elite.

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
grep "^val_bpb:\|^peak_vram_mb:\|^num_params_M:" logs/exp0007.log
```

If the grep output is empty, the run crashed. Read the Python stack trace:

```bash
tail -n 50 logs/exp0007.log
```

## Logging results

When an experiment is done, log it to `results.tsv` (tab-separated, NOT comma-separated).

The TSV has a header row and 10 columns:

```text
exp_id	commit	parent1	parent2	val_bpb	memory_gb	params_m	status	mutation_kind	description
```

1. experiment id, e.g. `exp0007`
2. git commit hash (short, 7 chars)
3. parent1 tag or commit
4. parent2 tag or `-`
5. val_bpb achieved — use 0.000000 for crashes
6. peak memory in GB, round to .1f — use 0.0 for crashes
7. parameter count in millions — use 0.0 for crashes if unavailable
8. status: `elite`, `discard`, or `crash`
9. mutation kind: `baseline`, `mutate`, or `crossover`
10. short text description of what this experiment tried

Example:

```text
exp_id	commit	parent1	parent2	val_bpb	memory_gb	params_m	status	mutation_kind	description
exp0001	a1b2c3d	-	-	0.997900	44.0	50.3	elite	baseline	baseline
exp0002	b2c3d4e	elite/0	-	0.996800	44.3	50.3	elite	mutate	increase matrix lr
exp0003	c3d4e5f	elite/0	-	1.005000	44.0	50.3	discard	mutate	switch to GeLU activation
exp0004	d4e5f6g	elite/1	elite/0	0.996900	43.1	48.8	elite	crossover	combine lower width with better schedule
exp0005	e5f6g7h	elite/2	-	0.000000	0.0	0.0	crash	mutate	double model width (OOM)
```

## Logging the population

`population.tsv` is the current elite pool only. Rewrite it whenever the elite pool changes.

The TSV has a header row and 10 columns:

```text
elite_id	tag	commit	val_bpb	memory_gb	params_m	role	parent1	parent2	description
```

1. elite slot id
2. elite tag
3. current commit hash for that elite
4. current val_bpb
5. current memory in GB
6. current parameter count in millions
7. role: `best`, `lean`, or `diverse`
8. parent1
9. parent2
10. short description

Example:

```text
elite_id	tag	commit	val_bpb	memory_gb	params_m	role	parent1	parent2	description
0	elite/0	b2c3d4e	0.996800	44.3	50.3	best	elite/0	-	increase matrix lr
1	elite/1	d4e5f6g	0.996900	43.1	48.8	lean	elite/1	elite/0	combine lower width with better schedule
2	elite/2	f6g7h8i	0.997100	42.7	47.9	diverse	elite/0	-	smaller model with altered init
```

## Committing artifacts

Everything the run produces must end up in git. Nothing is allowed to stay untracked. This applies to all of: `logs/*.log`, `reflections/*.md`, `results.tsv`, and `population.tsv`.

Concretely:

- After every experiment step, stage and commit all artifacts produced by that step (see step 15 in the experiment loop).
- If `git status` ever shows untracked or modified files under the artifact paths above, commit them before moving on.

## Reflections

For every experiment, write a short reflection file under `reflections/`, e.g. `reflections/exp0007.md`.

Keep it short, structured, and numerical. Prefer exact values and deltas over vague words.

Each reflection should record:

- what changed
- the parent metrics
- the child metrics
- the deltas
- the decision
- whether and when the idea should be revisited
- which prior experiment it is closest to

Example:

```md
# exp0007

parent1: elite/2
parent2: -
mutation_kind: mutate
closest_prior: exp0004

change_summary:

- short_window: 1024 -> 1536
- optimizer: unchanged
- init: unchanged
- width/depth: unchanged

parent_metrics:

- val_bpb: 0.997100
- memory_gb: 42.7
- params_m: 47.9

child_metrics:

- val_bpb: 0.996850
- memory_gb: 43.6
- params_m: 47.9

deltas:

- delta_val_bpb: -0.000250
- delta_memory_gb: +0.9
- delta_params_m: +0.0

decision:

- status: elite
- replace_slot: elite/2

judgment:

- worth_it: yes
- reason: 0.000250 val_bpb gain for +0.9 GB is acceptable

revisit_later:

- yes
- condition: retry only together with width reduction or lower KV-head cost
```

## Parent choice and search moves

Choose parents deliberately. Do not overexploit a single elite.

### Hard parent-choice rules

1. **Do not use the same parent as `parent1` more than 2 completed experiments in a row** if another elite exists.
2. **In any block of 6 completed non-crash experiments, at least 3 different elites must appear as `parent1`** if 3 or more elites exist.
3. **When choosing a mutation parent, prefer the least recently used viable elite**.
4. **Do not keep starting from the current best**. They are all candidates.
5. **If a new elite was created in the last 2 completed experiments, prioritize using it or crossing it with another elite.**

### Hard crossover rules

1. **In any block of 6 completed non-crash experiments, at least 2 must be `crossover`** if at least 2 elites exist.
2. **After creating a new elite, one of the next 2 completed non-crash experiments must be a crossover involving that new elite** if another elite exists.
3. **For crossover, use two materially different parents when possible**:
   - different roles, or
   - different descriptions, or
   - different recent mutation history
4. **Do not do raw git merge of `train.py`**. Crossover must be semantic and intentional.

### Search move schedule

Use this default pattern once there are at least 3 elites:

1. mutation from a non-recent parent
2. mutation from a different parent
3. crossover between two different elites
4. mutation from the least recently used elite
5. crossover involving the newest elite
6. free choice, but do not violate the hard rules above

This schedule is a guide, not a prison. The hard rules dominate.

### Fine-tuning rule

Do not get trapped in one-dimensional sweeps.

If you try 3 nearby values of the same knob and the original or best-known setting is still best, stop sweeping that knob and change direction.

Example:

- tried MATRIX_LR = 0.04, 0.06, 0.08
- none beat the current best
- stop tuning MATRIX_LR for now and mutate architecture, init, attention pattern, width, depth, or schedule shape instead

## Choosing parents

When proposing a new child, first read:

- `population.tsv`
- the last few rows of `results.tsv`
- relevant reflections
- the current `train.py`

Use one of two modes:

### 1. Mutation

Choose one elite and improve it.

Example:

- Parent: `elite/2`
- Child idea: keep the architecture, change only the learning rate schedule

### 2. Semantic crossover

Choose two elites. Use one parent as the base code and intentionally transplant one coherent idea from the other parent.

Example:

- Parent A: lower-memory smaller model
- Parent B: better optimizer schedule
- Child: start from Parent A code, then add Parent B's schedule only

## Spawning a child

To spawn a child from an elite:

```bash
git switch autoresearch/<tag>
git reset --hard elite/2
```

This does **not** create a new branch. It means:

- stay on the working branch
- move that branch so it points at the elite commit
- make the files on disk match that elite exactly

Now modify `train.py`, commit, and run the experiment.

Example:

```bash
git switch autoresearch/apr10-gen1
git reset --hard elite/2
# edit train.py
git add train.py
git commit -m "try larger short attention window"
uv run train.py > logs/exp0008.log 2>&1
```

If the run is good enough, the child may enter the population. If not, it remains only in `results.tsv` and `reflections/`.

## Elite selection

When deciding whether a child should enter the pool, reason in this order:

1. **val_bpb is primary**.
2. **Memory is secondary**.
3. **Simplicity matters**.
4. **Diversity matters**.
5. **Stability matters**.

Practical guidance:

- A clear val_bpb improvement should usually enter the pool.
- A tie or near-tie with lower memory or simpler code is a strong candidate.
- A slightly worse result may still deserve a slot if it is much cheaper, much simpler, or materially different from the current elites.
- Crashy ideas never enter the pool.

## Replacing elites

If a child enters the pool, it does **not** have to replace its own parent.

Ask:

- Which current elite should this child replace?

Possible answers:

- its parent, if it is clearly a better version of that parent
- the weakest elite overall
- the most redundant elite
- an empty slot, if the pool is not full yet

Examples:

- A child born from `elite/2` might replace `elite/2`.
- A child born from `elite/2` might actually be the new `best`, so it could replace `elite/0`.
- A child born from `elite/3` might be a better low-memory candidate, so it could replace the current `lean` elite.

To promote a child into a slot, move the chosen tag:

```bash
git tag -f elite/1 HEAD
```

Then rewrite `population.tsv` to reflect the new elite pool.

## The experiment loop

The experiment runs on a dedicated working branch, e.g. `autoresearch/apr10-gen1`.

LOOP FOREVER:

1. Look at the git state: the current branch/commit and the current elite tags.
2. Read `population.tsv`, recent `results.tsv`, and relevant reflections.
3. Choose a search move that satisfies the hard parent-choice and crossover rules.
4. Reset the working branch to the chosen parent commit:
   - `git switch autoresearch/<tag>`
   - `git reset --hard <chosen-parent-tag>`
5. Tune `train.py` with an experimental idea by directly hacking the code.
6. git commit
7. Run the experiment:
   - `uv run train.py > logs/<exp_id>.log 2>&1`
8. Read out the results:
   - `grep "^val_bpb:\|^peak_vram_mb:\|^num_params_M:" logs/<exp_id>.log`
9. If the grep output is empty, the run crashed. Run `tail -n 50 logs/<exp_id>.log` to read the Python stack trace and attempt a fix. If you cannot get things to work after more than a few attempts, give up.
10. Record the result in `results.tsv`.
11. Write a short reflection.
12. Decide whether the child should enter the elite pool.
13. If yes, move the chosen elite tag, update `population.tsv`, and keep going.
14. If no, leave the elite tags unchanged and keep going.
15. Commit all artifacts produced by this step:
    - `git add logs/<exp_id>.log reflections/<exp_id>.md results.tsv population.tsv`
    - `git commit -m "exp <exp_id>: artifacts"` (skip if `git status` shows nothing staged)
16. Verify nothing is left untracked: `git status` should be clean under the artifact paths.

The idea is that you are a completely autonomous researcher trying things out. Some children become elites, some do not. You are not maintaining one line of progress. You are maintaining a small pool of strong candidates and exploring around them.

**Timeout**: Each experiment should take ~5 minutes total (+ a few seconds for startup and eval overhead). If a run exceeds 10 minutes, kill it and treat it as a failure.

**Crashes**: If a run crashes (OOM, or a bug, or etc.), use your judgment. If it is something dumb and easy to fix, fix it and re-run. If the idea itself is fundamentally broken, just log `crash` in `results.tsv` and move on.

**NEVER STOP**: Once the experiment loop has begun, do NOT pause to ask the human if you should continue. Do NOT ask "should I keep going?". The loop runs until the human interrupts you.

## Important reminders

- Only edit `train.py`.
- Never edit `prepare.py`.
- Never change the evaluation harness.
- Maintain `results.tsv`, `population.tsv`, `logs/`, and `reflections/`.
- Commit every artifact every step. Nothing untracked.
- Use the working branch as a movable workspace.
- Use elite tags as the durable population.
- Prefer semantic crossover, not raw textual merges.
- Be clear in your descriptions. The bookkeeping files are your memory.
