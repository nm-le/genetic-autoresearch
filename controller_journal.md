# Controller journal — apr30-h100long-opus47-trace-selfmod-2

This file is the human-readable memory of why `trace.py` changed across this run.
Every controller-improvement step appends one entry describing the problem, the
planned change, and what behavior should change. After editing `trace.py`, a
follow-up note records what actually changed and the compile sanity check.

---

## 2026-04-30T23:32 — pre-edit note (controller_sha=b233d7b98f69)

**Problem**: at exp0003 the controller suggested `crossover` with primary=elite/1
(DEPTH=9 mutation, val=1.018) and secondary=elite/0 (baseline). The fallback in
`choose_secondary` picks the baseline only because `choose_secondary`'s loop
explicitly skips baseline elites first, and with no other elites available it
falls back to picking the baseline anyway. This is a degenerate crossover —
the baseline carries no "idea" to transplant.

Root cause is in `choose_operator`: the "newest-promotion" trigger forces
crossover as soon as a fresh elite is added, but it does not check whether
there are at least two non-baseline elites available. With a frontier of
{baseline, single-mutate} the only viable secondary is the baseline, which
the existing logic in `choose_secondary` correctly tries to avoid.

**Planned change**: in `choose_operator`, before returning `crossover` from
any branch, check that the frontier has ≥2 elites whose `mutation_kind` is
not `baseline`. If not, return `mutate` instead. This is a one-place gate
that makes the operator decision align with what `choose_secondary` can
actually deliver.

**Expected effect**: while the frontier still contains only one non-baseline
parent, all suggestions will be `mutate` (correctly using the only good
parent we have). Once a second non-baseline elite enters the frontier, the
existing crossover triggers reactivate normally.

## 2026-04-30T23:33 — post-edit note (controller_sha=d650fa1fc126)

**What changed**: Added a single early-return in `choose_operator` after the
existing `len(frontier) < 2` guard: if fewer than 2 non-baseline elites
exist in the frontier, return `mutate`. 9 lines added, no other logic
touched.

**Compile**: `python -m py_compile trace.py` → ok.

**Confirmed behavior change**: re-running `python trace.py suggest` with
the same frontier (elite/0 baseline + elite/1 DEPTH=9) now returns
`operator=mutate, parent1=80d458b (elite/1)` instead of the previous
degenerate `operator=crossover, parent2=elite/0 (baseline)`.

---

## 2026-04-30T23:42 — pre-edit note (controller_sha=d650fa1fc126)

**Problem**: at exp0004 the controller again suggested a degenerate
crossover: primary=elite/2 (depth=9 + warmdown=0.3, val=1.020),
secondary=elite/1 (depth=9, val=1.018). But elite/2's `parent1` is
elite/1's commit — so elite/1 is the direct conceptual ancestor of
elite/2, and the only "idea" elite/1 carries (DEPTH=9) is already in
elite/2. Crossover between a parent and its direct child has no
information content; transplanting any non-redundant property would
either revert the child's mutation or be invented out of thin air
(deviation from suggestion).

The previous (just-installed) `non_baseline_elites < 2` gate doesn't
catch this because we now have 2 non-baseline elites — they just happen
to share the same lineage.

**Planned change**: introduce a "lineage-independent" notion. Two
non-baseline elites A and B are lineage-independent iff neither's
`parent1` commit equals the other's `commit`. Add:

1. A helper `_lineage_independent(a, b)` that does the direct
   parent/child check.
2. In `choose_operator`, replace the `non_baseline_elites < 2` count with
   "exists a pair of lineage-independent non-baseline elites" (using the
   helper). If no such pair, return `mutate`.
3. In `choose_secondary`, also skip secondaries that are not
   lineage-independent of `primary`. Keep the existing description-distance
   filter. The fallback (which ignores filters) stays as a last resort.

This is conservative: it still allows crossover once the search produces
two non-baseline elites from disjoint mutation chains.

**Expected effect**: with the current frontier (elite/0 baseline +
elite/1 depth=9 + elite/2 depth=9+warmdown=0.3, where elite/2 is a
descendant of elite/1), no lineage-independent pair exists, so the
suggestion will become `mutate` from primary (whichever UCB picks).
After a future mutation off elite/0 lands, lineage-independence will
hold and crossover unlocks.

## 2026-04-30T23:43 — post-edit note (controller_sha=80540eb*)

**What changed**: Added helper `_lineage_independent(a, b)` (12 lines) and
two callers: a "has_independent_pair" gate inside `choose_operator` (10
lines) and a `_lineage_independent(primary, row)` skip filter inside
`choose_secondary`'s loop (4 lines). Total +40 lines, no other logic
touched.

**Compile**: `python -m py_compile trace.py` → ok.

**Confirmed behavior change**: re-running `python trace.py suggest` with
the same frontier as before now returns `operator=mutate` instead of the
degenerate `operator=crossover, parent2=elite/1`.

---

## 2026-05-01T00:02 — pre-edit note (controller_sha=786d99d6529e)

**Problem**: at exp0006 the controller suggested crossover(primary=elite/1
depth=9 val=1.018, secondary=elite/2-new depth=8+warmdown=0.3 val=0.999).
Lineage-independent check passes because elite/1 and elite/2-new only
share a deeper common root (baseline). But the only "idea" elite/2-new
carries is `WARMDOWN_RATIO=0.3`, and applying it to elite/1's depth=9
base recreates exp0003's exact recipe — a duplicate experiment.

The deeper pathology is that `select_primary` keeps picking elites with
much-worse val_bpb than the best. Current frontier:
  elite/0 val=0.997 (best, baseline)
  elite/1 val=1.018 (much worse, depth=9)
  elite/2 val=0.999 (slightly worse)
  elite/3 val=1.013 (much worse)

UCB picks elite/1 because its expansions=0 and recency penalty is small,
and novelty/coverage favor it. UCB by design ignores raw quality and
relies on `mean_child_gain` to learn which parents are productive — but
with only 4 experiments worth of data, that's noisy. Meanwhile, elite/0
is *clearly* the best parent to mutate from.

**Planned change**: add a quality-gap penalty to the score in
`select_primary`. For each elite, compute `delta = val_bpb - best_val`
across the frontier and subtract `kappa * delta` from the score.
With `kappa = 2.0`, an elite that is 0.02 worse than best loses 0.04 in
score — large enough to outweigh the typical UCB explore (~0.05) +
novelty (~0.15 * 0.85) + coverage (~0.10 * 0.7) margins for moderately
worse elites, but not catastrophic enough to kill exploration entirely
when elites are close in quality.

**Expected effect**: with the current frontier, primary should switch to
elite/0 (best). That makes mutate-from-baseline the default, and the
only lineage-independent secondary (elite/3, since elite/1 and elite/2
are direct children of elite/0) carries a fresh idea (MATRIX_LR=0.05)
that hasn't been tried at depth=8.

## 2026-05-01T00:08 — post-edit note (controller_sha=ef98a3*)

**What changed**: Initial attempt was `quality_gap_penalty` added to
`select_primary` scoring with `kappa=2`, then `kappa=5`. Debug print
showed UCB's recency penalty (-0.2 for age=0) and the negative
mean_child_gain on elite/0 (-0.011, dragged down by both DEPTH=9 and
WARMDOWN=0.3 worse-children) were too dominant for a pure quality
penalty to overcome at any reasonable kappa.

Pivoted to a hard rule instead: `select_primary` now does a quality-first
selection — pick the lowest-val_bpb elite directly while its expansion
count is < 3. Falls back to the existing UCB+novelty+coverage scoring
afterwards. Removed the `quality_gap_penalty` function (never paid off
in the score; the hard rule subsumes it). +21 lines / -16 lines net.

**Compile**: `python -m py_compile trace.py` → ok.

**Confirmed behavior change**: re-suggest now produces
`crossover(primary=elite/0, secondary=elite/3)` — the previous
elite/1+elite/2 degenerate crossover is gone, and the new suggestion
carries a fresh idea (MATRIX_LR=0.05) onto the baseline base.

---

## 2026-05-01T04:51 — pre-edit note (controller_sha=9ab45400f34e)

**Problem**: at exp0020 the controller suggested
`crossover(primary=elite/0=b26413d, secondary=elite/2=451f99b)`. The
direct-parent lineage check passed because elite/0.parent1=c57cda9 and
elite/2.parent1=02c9a8c — neither equals the other's commit. But elite/2
is a *grandparent* of elite/0 in the conceptual chain
(b26413d → c57cda9 → 451f99b → 02c9a8c → 0558e1a → fcc3407). So
elite/2's mutation idea (EMBEDDING_LR=0.5) is already in elite/0 by
inheritance through c57cda9. The crossover would be a no-op + noise.

**Planned change**: replace the direct parent/child check in
`_lineage_independent` with full conceptual-ancestor walks. Build a
helper `_conceptual_ancestors(commit, results)` that walks the parent1
chain via `results.tsv` and returns the set of all ancestor commits.
Two elites are lineage-independent iff neither's commit appears in the
other's ancestor set.

Pass `past_results` (loaded once in `cmd_suggest`) through to
`choose_operator` and `choose_secondary` so they can call
`_lineage_independent` with results context.

**Expected effect**: with the current frontier (elite/2 is an ancestor
of elite/0), the suggestion should switch to a non-degenerate
operator: either mutate from elite/0, or crossover with elite/1 or
elite/3 (the only lineage-independent secondaries).

## 2026-05-01T04:54 — post-edit note (controller_sha=ce4*)

**What changed**: Added `_conceptual_ancestors(commit, results)` helper
that walks the parent1 chain via results.tsv. Updated
`_lineage_independent` to take an optional `results` parameter and use
ancestor sets when provided (fallback to direct-only check otherwise).
Threaded `results` through `choose_operator`, `choose_secondary`, and
`cmd_suggest`. ~30 lines added, ~10 lines modified.

**Compile**: `python -m py_compile trace.py` → ok.

**Confirmed behavior change**: re-suggest now produces
`crossover(primary=elite/0=b26413d, secondary=elite/1=a2abd27)` —
elite/2 (which is in elite/0's deep ancestry) is correctly skipped.
elite/1 and elite/0 share only a common ancestor 02c9a8c, neither is
the other's ancestor.

---

## 2026-05-01T05:09 — pre-edit note (controller_sha=8b2b8cb57f10)

**Problem**: at exp0022 the suggestion is again
`crossover(elite/0=b26413d, elite/1=a2abd27)`. Pair_history shows that
exact pair was used in exp0020 (key `a2abd27|b26413d` → 1). With the
current frontier, elite/2 and elite/3 are direct children of elite/0
(fail multi-hop lineage), leaving elite/1 as the *only* viable
secondary. The existing `pair_penalty = 0.15 * used` is too weak to
flip the choice when there are no alternatives.

**Planned change**: in `choose_operator`, after the lineage-independent
gate, add an "untried pair exists" gate. If every lineage-independent
pair of non-baseline elites has been crossed at least once, return
`mutate` instead. This avoids re-running the same crossover when the
search has exhausted the set of unique informative crosses.

**Expected effect**: with the current frontier (only 1 viable pair, and
that pair already used), the operator becomes `mutate` from the
quality-first primary (elite/0). That gives the search room to keep
mutating elite/0 until a new lineage opens up via elite/1's promotion.

## 2026-05-01T05:11 — post-edit note (controller_sha=*)

**What changed**: Added two related gates. First, in `choose_operator`,
the existing lineage-pair check is augmented to also require that at
least one such pair is *untried* (not in `pair_history`). Second, in
`cmd_suggest`, after `select_primary` and `choose_operator`, if the
chosen primary itself has no untried lineage-independent partner, the
operator is downgraded to `mutate`. The first gate addresses the global
case (no useful crosses anywhere); the second handles the local case
(this primary specifically has nothing fresh to cross with). +27 lines.

**Compile**: `python -m py_compile trace.py` → ok.

**Confirmed behavior change**: re-suggest with the current frontier
(primary=elite/0 has only elite/1 as a viable partner, and that pair
was used in exp0020) now produces `mutate` from elite/0 instead of the
duplicate crossover.

---

## 2026-05-01T06:57 — pre-edit note (controller_sha=621eb12717df)

**Problem**: at exp0037 the suggestion is `crossover(elite/0=dbbdc5a,
elite/1=c1c146d)`. The "idea" elite/1 carries (warmdown=0.6) is already
in elite/0 — but only via the parent2 chain. elite/0's full lineage is:

  dbbdc5a (parent1=799f60f, parent2=0b91c83)
    parent2 0b91c83 was exp0033, which had parent2=c1c146d=elite/1

So elite/1 IS a conceptual ancestor of elite/0 once parent2 chains are
included. `_conceptual_ancestors` currently walks only parent1, so it
misses this. The suggested crossover would produce an exact duplicate
of elite/0's train.py (no diff).

**Planned change**: extend `_conceptual_ancestors` to BFS-walk both
parent1 and parent2 chains. This conservatively over-counts ancestry
(parent2 in crossover doesn't structurally inherit train.py the way
parent1 does), but the conservative behavior is correct here: if
donor's mutation has been *applied* to base via any prior crossover,
re-applying it is degenerate.

**Expected effect**: re-suggest will skip elite/1 as a secondary for
elite/0, falling through to either mutate or crossover with a different
elite. With current frontier, this likely produces mutate from elite/0.

## 2026-05-01T06:59 — post-edit note

**What changed**: Replaced the linear parent1-only walk in
`_conceptual_ancestors` with a BFS that follows both parent1 and
parent2. Same set semantics; now strictly more conservative about
classifying elites as related.

**Compile**: `python -m py_compile trace.py` → ok.

**Confirmed behavior change**: re-suggest now produces `mutate` from
elite/0 instead of the no-op crossover with elite/1.

---

## 2026-05-01T20:32 — pre-edit note (controller_sha=4d1e74ae8c7f)

**Problem**: the controller has now produced the same crossover pair
(elite/1=1cc15d7, elite/2=33420fe, idea=rotary=20000) 3 times in a row
(exp0098/exp0100/exp0102), producing near-duplicate val_bpb values
~0.9794 each time. The pair_history shows count=2 for this pair before
exp0102. Yet the per-primary "untried partner" gate doesn't trigger
because elite/1 has other untried-but-lineage-related partners that
aren't selectable, and the existing `pair_penalty = 0.15 * used` is
too weak to overcome elite/2's novelty/coverage advantage in
choose_secondary's scoring.

**Planned change**: bump `pair_penalty` from `0.15 * used` to `0.5 * used`.
A pair that has been used twice now incurs a -1.0 score penalty, far
more than any expected novelty/coverage gain (~0.15-0.25). This should
strongly discourage repeating the same pair while still allowing it
in the rare case all alternatives are also exhausted.

**Expected effect**: the next suggestion will pick a different
secondary (e.g. elite/3) or fall through to mutate.

## 2026-05-01T20:33 — post-edit note

**What changed**: `pair_penalty = 0.5 * used` (was `0.15 * used`).
1-line edit.

**Compile**: ok.

**Confirmed behavior change**: re-suggest now produces `mutate` from
elite/3 instead of the duplicate crossover. The 3-way deadlock around
the (elite/1, elite/2) pair is broken.



