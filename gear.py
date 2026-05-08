#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path.cwd()
STATE_PATH = ROOT / "gear_state.json"
RESULTS_PATH = ROOT / "results.tsv"
FRONTIER_PATH = ROOT / "frontier.tsv"
CONTROLLER_EVENTS_PATH = ROOT / "controller_events.tsv"
REFLECTIONS_DIR = ROOT / "reflections"
LOGS_DIR = ROOT / "logs"

RESULTS_HEADER = [
    "exp_id",
    "commit",
    "parent1",
    "parent2",
    "val_bpb",
    "memory_gb",
    "params_m",
    "status",
    "mutation_kind",
    "description",
    "controller_sha",
    "promoted_slot",
]

FRONTIER_HEADER = [
    "slot",
    "tag",
    "commit",
    "val_bpb",
    "memory_gb",
    "params_m",
    "role",
    "parent1",
    "parent2",
    "mutation_kind",
    "description",
    "controller_sha",
    "expansions",
    "mean_child_gain",
    "last_used_exp",
    "last_improved_exp",
]

EVENTS_HEADER = ["step", "event", "detail", "controller_sha"]

DEFAULT_STATE = {
    "run_tag": None,
    "population_size": 4,
    "next_exp": 1,
    "history": [],
    "operator_history": [],
    "pair_history": {},
}


@dataclass
class Suggestion:
    operator: str
    parent1: str          # commit hash (immutable reference)
    parent1_tag: str      # elite slot tag (for git reset convenience)
    parent2: str          # commit hash or "-"
    parent2_tag: str      # elite slot tag or "-"
    rationale: str


def read_tsv(path: Path) -> List[Dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        return list(reader)


def write_tsv(path: Path, header: List[str], rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in header})


def ensure_file(path: Path, header: List[str]) -> None:
    if not path.exists():
        write_tsv(path, header, [])


def load_state() -> Dict[str, Any]:
    if not STATE_PATH.exists():
        return dict(DEFAULT_STATE)
    with STATE_PATH.open("r", encoding="utf-8") as f:
        state = json.load(f)
    merged = dict(DEFAULT_STATE)
    merged.update(state)
    return merged


def save_state(state: Dict[str, Any]) -> None:
    with STATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)


def controller_sha() -> str:
    path = Path(__file__).resolve()
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()[:12]


def git_short_head() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True)
        return out.strip()
    except Exception:
        return "unknown"


def normalize_float(value: Any, digits: int = 6) -> str:
    return f"{float(value):.{digits}f}"


def normalize_float1(value: Any) -> str:
    return f"{float(value):.1f}"


def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


def jaccard_distance(a: str, b: str) -> float:
    ta, tb = set(tokenize(a)), set(tokenize(b))
    if not ta and not tb:
        return 0.0
    union = ta | tb
    inter = ta & tb
    return 1.0 - (len(inter) / max(1, len(union)))


def role_bucket(role: str) -> str:
    role = (role or "").strip().lower()
    if role in {"best", "lean", "diverse"}:
        return role
    return "other"


def mutation_bucket(kind: str, description: str) -> str:
    text = f"{kind} {description}".lower()
    if any(tok in text for tok in ["opt", "lr", "schedule", "decay", "momentum"]):
        return "optimizer"
    if any(tok in text for tok in ["depth", "width", "head", "window", "rope", "layer", "attn", "attention"]):
        return "architecture"
    if any(tok in text for tok in ["batch", "tokens", "throughput", "mfu"]):
        return "throughput"
    if any(tok in text for tok in ["init", "norm", "drop", "regular", "gelu", "activation"]):
        return "regularization"
    if kind == "crossover":
        return "crossover"
    return "misc"


def load_frontier() -> List[Dict[str, str]]:
    return read_tsv(FRONTIER_PATH)


def save_frontier(rows: List[Dict[str, Any]]) -> None:
    write_tsv(FRONTIER_PATH, FRONTIER_HEADER, rows)


def frontier_map() -> Dict[str, Dict[str, str]]:
    """Map from tag (elite slot) to frontier row."""
    return {row["tag"]: row for row in load_frontier() if row.get("tag")}


def frontier_map_by_commit(frontier: Optional[List[Dict[str, str]]] = None) -> Dict[str, Dict[str, str]]:
    """Map from commit hash to frontier row."""
    if frontier is None:
        frontier = load_frontier()
    return {row["commit"]: row for row in frontier if row.get("commit")}


def best_val(frontier: List[Dict[str, str]]) -> Optional[float]:
    vals = [float(r["val_bpb"]) for r in frontier if r.get("val_bpb")]
    return min(vals) if vals else None


def log_event(event: str, detail: str) -> None:
    rows = read_tsv(CONTROLLER_EVENTS_PATH)
    rows.append(
        {
            "step": str(len(rows) + 1),
            "event": event,
            "detail": detail,
            "controller_sha": controller_sha(),
        }
    )
    write_tsv(CONTROLLER_EVENTS_PATH, EVENTS_HEADER, rows)


def recency_penalty(row: Dict[str, str], state: Dict[str, Any]) -> float:
    last = row.get("last_used_exp", "")
    if not last:
        return 0.0
    m = re.match(r"exp(\d+)", last)
    if not m:
        return 0.0
    last_idx = int(m.group(1))
    current = int(state.get("next_exp", 1)) - 1
    age = current - last_idx
    if age <= 1:
        return -0.2
    if age <= 3:
        return -0.05
    return 0.0


def ucb_score(row: Dict[str, str], state: Dict[str, Any], total_expansions: int) -> float:
    mean_gain = float(row.get("mean_child_gain") or 0.0)
    expansions = int(float(row.get("expansions") or 0.0))
    beta = 0.05
    explore = beta * math.sqrt(math.log(total_expansions + 2.0) / (expansions + 1.0))
    return mean_gain + explore + recency_penalty(row, state)


def novelty_score(row: Dict[str, str], frontier: List[Dict[str, str]], state: Dict[str, Any]) -> float:
    history = state.get("history", [])[-3:]
    recently_used = [h["parent1"] for h in history if h.get("parent1")]
    peers = [r for r in frontier if r.get("commit") in recently_used and r.get("commit") != row.get("commit")]
    if not peers:
        peers = [r for r in frontier if r.get("commit") != row.get("commit")]
    if not peers:
        return 0.5
    src = f"{row.get('role','')} {row.get('mutation_kind','')} {row.get('description','')}"
    distances = [jaccard_distance(src, f"{p.get('role','')} {p.get('mutation_kind','')} {p.get('description','')}") for p in peers]
    return min(distances)


def coverage_score(row: Dict[str, str], frontier: List[Dict[str, str]]) -> float:
    bucket = (role_bucket(row.get("role", "")), mutation_bucket(row.get("mutation_kind", ""), row.get("description", "")))
    density = 0
    for peer in frontier:
        peer_bucket = (role_bucket(peer.get("role", "")), mutation_bucket(peer.get("mutation_kind", ""), peer.get("description", "")))
        if peer_bucket == bucket:
            density += 1
    return 1.0 / math.sqrt(density + 1.0)


def select_primary(frontier: List[Dict[str, str]], state: Dict[str, Any]) -> Dict[str, str]:
    total_expansions = max(1, sum(int(float(r.get("expansions") or 0.0)) for r in frontier))
    scored: List[Tuple[float, Dict[str, str]]] = []
    current_step = int(state.get("next_exp", 1))
    lam = 0.15 if current_step <= 12 else 0.08
    gamma = 0.10 if current_step <= 12 else 0.05
    for row in frontier:
        score = ucb_score(row, state, total_expansions)
        score += lam * novelty_score(row, frontier, state)
        score += gamma * coverage_score(row, frontier)
        scored.append((score, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def choose_operator(frontier: List[Dict[str, str]], state: Dict[str, Any]) -> str:
    if len(frontier) < 2:
        return "mutate"

    recent_noncrash = [op for op in state.get("operator_history", [])[-5:] if op != "crash"]
    crossover_count = sum(1 for op in recent_noncrash if op == "crossover")

    # Hard trigger: force crossover if none in last 4 non-crash ops
    if len(recent_noncrash) >= 4 and crossover_count < 1:
        return "crossover"

    # Soft trigger: target ~25-30% crossover rate after warmup phase
    all_ops = [op for op in state.get("operator_history", []) if op != "crash"]
    total_ops = len(all_ops)
    if total_ops >= 3:
        total_crossovers = sum(1 for op in all_ops if op == "crossover")
        crossover_rate = total_crossovers / max(1, total_ops)
        if crossover_rate < 0.25:
            return "crossover"

    last = recent_noncrash[-1] if recent_noncrash else None
    if last == "crossover":
        return "mutate"

    # Trigger crossover after a new promotion (fresh elite to combine)
    newest_exp = None
    newest_tag = None
    for row in frontier:
        exp = row.get("last_improved_exp") or row.get("last_used_exp")
        if exp and re.match(r"exp(\d+)", exp):
            idx = int(re.match(r"exp(\d+)", exp).group(1))
            if newest_exp is None or idx > newest_exp:
                newest_exp = idx
                newest_tag = row.get("tag")
    if newest_tag and len(frontier) >= 2:
        history = state.get("history", [])[-2:]
        if any(h.get("promoted_slot") == newest_tag for h in history):
            return "crossover"

    return "mutate"


def choose_secondary(primary: Dict[str, str], frontier: List[Dict[str, str]], state: Dict[str, Any]) -> Dict[str, str]:
    pair_history = state.get("pair_history", {})
    best_score = None
    best_row = None
    primary_text = f"{primary.get('role','')} {primary.get('description','')} {primary.get('mutation_kind','')}"

    for row in frontier:
        if row.get("tag") == primary.get("tag"):
            continue

        # Skip baseline elites — they have no "idea" to transplant
        if row.get("mutation_kind") == "baseline":
            continue

        # Skip elites whose description is too similar to primary (degenerate crossover)
        row_text = f"{row.get('role','')} {row.get('description','')} {row.get('mutation_kind','')}"
        desc_dist = jaccard_distance(primary.get("description", ""), row.get("description", ""))
        if desc_dist < 0.3:
            continue

        complement = jaccard_distance(primary_text, row_text)
        role_bonus = 0.2 if role_bucket(primary.get("role", "")) != role_bucket(row.get("role", "")) else 0.0

        # Prefer better val_bpb secondaries (they carry proven ideas)
        val_bonus = 0.0
        try:
            val_bonus = 0.1 if float(row.get("val_bpb", 1.0)) < float(primary.get("val_bpb", 1.0)) else 0.0
        except (ValueError, TypeError):
            pass

        pair_key = "|".join(sorted([primary.get("commit", ""), row.get("commit", "")]))
        used = pair_history.get(pair_key, 0)
        pair_penalty = 0.15 * used

        val = complement + role_bonus + val_bonus - pair_penalty
        if best_score is None or val > best_score:
            best_score = val
            best_row = row

    if best_row is None:
        # Fallback: if all candidates were filtered, pick the most different one ignoring filters
        for row in frontier:
            if row.get("tag") == primary.get("tag"):
                continue
            row_text = f"{row.get('role','')} {row.get('description','')} {row.get('mutation_kind','')}"
            complement = jaccard_distance(primary_text, row_text)
            if best_score is None or complement > best_score:
                best_score = complement
                best_row = row

    if best_row is None:
        raise RuntimeError("No viable secondary parent found")
    return best_row


def next_exp_id(state: Dict[str, Any]) -> str:
    return f"exp{int(state.get('next_exp', 1)):04d}"


def cmd_init(args: argparse.Namespace) -> int:
    state = load_state()
    state["run_tag"] = args.run_tag
    state["population_size"] = args.population_size
    save_state(state)
    LOGS_DIR.mkdir(exist_ok=True)
    REFLECTIONS_DIR.mkdir(exist_ok=True)
    ensure_file(RESULTS_PATH, RESULTS_HEADER)
    ensure_file(FRONTIER_PATH, FRONTIER_HEADER)
    ensure_file(CONTROLLER_EVENTS_PATH, EVENTS_HEADER)
    log_event("init", f"run_tag={args.run_tag}, population_size={args.population_size}")
    print(f"Initialized GEAR controller for run_tag={args.run_tag}")
    print(f"Next experiment id: {next_exp_id(state)}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    state = load_state()
    frontier = load_frontier()
    print(json.dumps(
        {
            "run_tag": state.get("run_tag"),
            "next_exp": next_exp_id(state),
            "controller_sha": controller_sha(),
            "frontier_size": len(frontier),
            "frontier": frontier,
            "recent_history": state.get("history", [])[-5:],
        },
        indent=2,
    ))
    return 0


def cmd_suggest(args: argparse.Namespace) -> int:
    state = load_state()
    frontier = load_frontier()
    if not frontier:
        suggestion = Suggestion(
            operator="baseline",
            parent1="-",
            parent1_tag="-",
            parent2="-",
            parent2_tag="-",
            rationale="No frontier yet. Run the unmodified baseline and promote it into elite/0.",
        )
        print(json.dumps(asdict(suggestion), indent=2))
        return 0
    primary = select_primary(frontier, state)
    operator = choose_operator(frontier, state)
    if operator == "mutate":
        suggestion = Suggestion(
            operator="mutate",
            parent1=primary["commit"],
            parent1_tag=primary["tag"],
            parent2="-",
            parent2_tag="-",
            rationale=f"Primary parent chosen by UCB + novelty + coverage. "
                      f"Base: {primary['tag']} ({primary.get('description', 'no description')}). "
                      f"Do one coherent mutation from this base.",
        )
    else:
        secondary = choose_secondary(primary, frontier, state)
        suggestion = Suggestion(
            operator="crossover",
            parent1=primary["commit"],
            parent1_tag=primary["tag"],
            parent2=secondary["commit"],
            parent2_tag=secondary["tag"],
            rationale=f"Base: {primary['tag']} ({primary.get('description', 'no description')}). "
                      f"Transplant idea from {secondary['tag']}: {secondary.get('description', 'no description')}.",
        )
    print(json.dumps(asdict(suggestion), indent=2))
    return 0


def decide_role(candidate: Dict[str, Any], frontier: List[Dict[str, str]]) -> str:
    if not frontier:
        return "best"
    best = min(frontier, key=lambda r: float(r["val_bpb"]))
    if float(candidate["val_bpb"]) < float(best["val_bpb"]):
        return "best"
    if candidate["memory_gb"] <= min(float(r["memory_gb"]) for r in frontier):
        return "lean"
    return "diverse"


def should_promote(candidate: Dict[str, Any], frontier: List[Dict[str, str]]) -> Tuple[bool, Optional[str], str]:
    status = candidate["status"]
    if status == "crash":
        return False, None, "crash"
    if not frontier:
        return True, "elite/0", "baseline frontier"

    c_val = float(candidate["val_bpb"])
    c_mem = float(candidate["memory_gb"])
    best = min(frontier, key=lambda r: float(r["val_bpb"]))
    worst = max(frontier, key=lambda r: float(r["val_bpb"]))
    best_val_ = float(best["val_bpb"])
    worst_val_ = float(worst["val_bpb"])

    improvement_margin = 0.000150
    tie_margin = 0.000120

    if len(frontier) < load_state().get("population_size", 4):
        next_slot = f"elite/{len(frontier)}"
        return True, next_slot, "frontier not full"

    if c_val < best_val_ - improvement_margin:
        return True, best["tag"], "new global best"

    if c_val < worst_val_ - improvement_margin:
        # Check if candidate improved its own parent's slot
        for row in frontier:
            if row["commit"] == candidate.get("parent1") and c_val <= float(row["val_bpb"]) - 0.000050:
                return True, row["tag"], "improved parent slot"
        return True, worst["tag"], "strictly stronger than weakest elite"

    close_to_best = abs(c_val - best_val_) <= tie_margin
    if close_to_best and c_mem < float(best["memory_gb"]) - 0.5:
        return True, best["tag"], "near tie with meaningful memory savings"

    # Diversity replacement: replace most redundant elite if candidate is distinct and not much worse.
    diverse_pool = []
    cand_text = f"{candidate['mutation_kind']} {candidate['description']}"
    for row in frontier:
        row_text = f"{row['mutation_kind']} {row['description']}"
        dist = jaccard_distance(cand_text, row_text)
        diverse_pool.append((dist, row))
    nearest_dist, nearest = min(diverse_pool, key=lambda x: x[0])
    if nearest_dist > 0.65 and c_val <= worst_val_ + 0.000100:
        return True, worst["tag"], "keeps a materially different elite alive"

    return False, None, "did not clear promotion thresholds"


def move_git_tag(tag: str, commit: str) -> None:
    subprocess.check_call(["git", "tag", "-f", tag, commit])


def upsert_frontier_row(slot: str, row: Dict[str, Any], frontier: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    updated = []
    found = False
    for existing in frontier:
        if existing["tag"] == slot:
            updated.append(row)
            found = True
        else:
            updated.append(existing)
    if not found:
        updated.append(row)
    updated.sort(key=lambda r: r["tag"])
    return updated


def record_parent_update(frontier: List[Dict[str, str]], parent_commit: str, child_gain: float, exp_id: str) -> None:
    """Update expansion stats for a parent identified by commit hash."""
    for row in frontier:
        if row["commit"] == parent_commit:
            expansions = int(float(row.get("expansions") or 0.0))
            mean_gain = float(row.get("mean_child_gain") or 0.0)
            new_mean = (mean_gain * expansions + child_gain) / (expansions + 1)
            row["expansions"] = str(expansions + 1)
            row["mean_child_gain"] = normalize_float(new_mean)
            row["last_used_exp"] = exp_id
            return


def cmd_record_run(args: argparse.Namespace) -> int:
    state = load_state()
    frontier = load_frontier()
    results = read_tsv(RESULTS_PATH)
    exp_id = args.exp_id or next_exp_id(state)
    commit = args.commit or git_short_head()
    controller = controller_sha()

    if args.status == "crash":
        val_bpb = 0.0
        memory_gb = 0.0
        params_m = 0.0
    else:
        val_bpb = float(args.val_bpb)
        memory_gb = float(args.memory_gb)
        params_m = float(args.params_m)

    # Look up parent by commit hash in frontier
    parent_val = None
    commit_map = frontier_map_by_commit(frontier)
    if args.parent1 in commit_map:
        parent_val = float(commit_map[args.parent1]["val_bpb"])
    child_gain = 0.0 if parent_val is None or args.status == "crash" else (parent_val - val_bpb)

    candidate = {
        "commit": commit,
        "parent1": args.parent1,
        "parent2": args.parent2,
        "val_bpb": val_bpb,
        "memory_gb": memory_gb,
        "params_m": params_m,
        "status": args.status,
        "mutation_kind": args.mutation_kind,
        "description": args.description,
    }

    promote, slot, reason = should_promote(candidate, frontier)
    promoted_slot = slot if promote else "-"

    results.append(
        {
            "exp_id": exp_id,
            "commit": commit,
            "parent1": args.parent1,
            "parent2": args.parent2,
            "val_bpb": normalize_float(val_bpb) if args.status != "crash" else "0.000000",
            "memory_gb": normalize_float1(memory_gb) if args.status != "crash" else "0.0",
            "params_m": normalize_float1(params_m) if args.status != "crash" else "0.0",
            "status": "elite" if promote else args.status,
            "mutation_kind": args.mutation_kind,
            "description": args.description,
            "controller_sha": controller,
            "promoted_slot": promoted_slot,
        }
    )
    write_tsv(RESULTS_PATH, RESULTS_HEADER, results)

    # Update parent stats using commit hashes
    if args.parent1 not in {"-", ""}:
        record_parent_update(frontier, args.parent1, child_gain, exp_id)
    if args.parent2 not in {"-", ""} and args.parent2 in commit_map:
        record_parent_update(frontier, args.parent2, child_gain * 0.5, exp_id)

    if promote and slot is not None:
        role = decide_role(candidate, frontier)
        new_row = {
            "slot": slot.split("/")[-1],
            "tag": slot,
            "commit": commit,
            "val_bpb": normalize_float(val_bpb),
            "memory_gb": normalize_float1(memory_gb),
            "params_m": normalize_float1(params_m),
            "role": role,
            "parent1": args.parent1,
            "parent2": args.parent2,
            "mutation_kind": args.mutation_kind,
            "description": args.description,
            "controller_sha": controller,
            "expansions": "0",
            "mean_child_gain": "0.000000",
            "last_used_exp": exp_id,
            "last_improved_exp": exp_id,
        }
        frontier = upsert_frontier_row(slot, new_row, frontier)
        save_frontier(frontier)
        if args.apply_git and commit != "unknown":
            try:
                move_git_tag(slot, commit)
            except subprocess.CalledProcessError as exc:
                print(f"warning: failed to move git tag {slot}: {exc}", file=sys.stderr)
        log_event("promote", f"{exp_id} -> {slot}: {reason}")
    else:
        save_frontier(frontier)
        log_event("discard", f"{exp_id}: {reason}")

    state["next_exp"] = int(state.get("next_exp", 1)) + 1
    state.setdefault("history", []).append(
        {
            "exp_id": exp_id,
            "parent1": args.parent1,
            "parent2": args.parent2,
            "mutation_kind": args.mutation_kind,
            "promoted_slot": promoted_slot,
            "status": args.status,
            "val_bpb": normalize_float(val_bpb) if args.status != "crash" else "0.000000",
        }
    )
    op = args.mutation_kind if args.status != "crash" else "crash"
    state.setdefault("operator_history", []).append(op)
    if args.parent2 not in {"-", ""}:
        # Use commit hashes for pair history keys
        key = "|".join(sorted([args.parent1, args.parent2]))
        state.setdefault("pair_history", {})[key] = state.setdefault("pair_history", {}).get(key, 0) + 1
    save_state(state)

    print(
        json.dumps(
            {
                "exp_id": exp_id,
                "controller_sha": controller,
                "promote": promote,
                "promoted_slot": promoted_slot,
                "reason": reason,
                "child_gain_vs_parent1": round(child_gain, 6),
            },
            indent=2,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GEAR external controller for AutoResearch-style experiments")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Initialize GEAR bookkeeping")
    p_init.add_argument("--run-tag", required=True)
    p_init.add_argument("--population-size", type=int, default=4)
    p_init.set_defaults(func=cmd_init)

    p_status = sub.add_parser("status", help="Show current state and frontier")
    p_status.set_defaults(func=cmd_status)

    p_suggest = sub.add_parser("suggest", help="Suggest the next move")
    p_suggest.set_defaults(func=cmd_suggest)

    p_record = sub.add_parser("record-run", help="Record a finished experiment and update the frontier")
    p_record.add_argument("--exp-id")
    p_record.add_argument("--commit")
    p_record.add_argument("--parent1", required=True)
    p_record.add_argument("--parent2", default="-")
    p_record.add_argument("--mutation-kind", choices=["baseline", "mutate", "crossover"], required=True)
    p_record.add_argument("--description", required=True)
    p_record.add_argument("--status", choices=["ok", "crash"], required=True)
    p_record.add_argument("--val-bpb")
    p_record.add_argument("--memory-gb")
    p_record.add_argument("--params-m")
    p_record.add_argument("--apply-git", action="store_true")
    p_record.set_defaults(func=cmd_record_run)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.cmd == "record-run" and args.status == "ok":
        missing = [name for name in ["val_bpb", "memory_gb", "params_m"] if getattr(args, name) is None]
        if missing:
            parser.error(f"record-run with --status ok requires: {', '.join(missing)}")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())