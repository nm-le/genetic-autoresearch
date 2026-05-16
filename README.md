# GEAR 🧬: Genetic AutoResearch for Agentic Code Evolution

[![arXiv](https://img.shields.io/badge/arXiv-2605.13874-b31b1b.svg)](https://arxiv.org/abs/2605.13874)
[![Project Page](https://img.shields.io/badge/Project-Page-blue)](https://genetic-autoresearch.github.io/)

> **GEAR** is a drop-in search controller that replaces single-incumbent hill climbing in [AutoResearch](https://github.com/karpathy/autoresearch) with population-based frontier search over research states. Under identical environments and compute budgets, all GEAR variants outperform the AutoResearch baseline and achieve lower validation bits-per-byte.

<p align="center">
  <img src="progress.png" width="700" />
</p>

**Ahmadreza Jeddi**<sup>1,2,\*</sup>, **Minh Ngoc Le**<sup>1,2,\*</sup>, **Hakki C. Karaimer**<sup>3</sup>, **Konstantinos G. Derpanis**<sup>3,4</sup>, **Babak Taati**<sup>1,2</sup>

<sup>1</sup>University of Toronto &nbsp; <sup>2</sup>Vector Institute &nbsp; <sup>3</sup>AI Center-Toronto, Samsung Electronics &nbsp; <sup>4</sup>York University

<sup>\*</sup>Equal contribution

## Overview

Autonomous research agents like AutoResearch iterate on a training script by editing code, running experiments, and keeping only improvements. However, this single-incumbent hill climbing prematurely discards valuable search signal — complementary local optima, partially successful ideas, and accumulated insights from diverse directions.

**GEAR** maintains a bounded population of elite nodes, selects parents using a composite score that balances productivity, novelty, and coverage, and expands the frontier through **mutation** (single-parent code edits) and **crossover** (transplanting ideas across complementary parents). Each node preserves code changes, reflections, parentage, and performance statistics that inform future expansion.

We study three variants:

| Variant | Search Policy | Description |
|---|---|---|
| **GEAR-Prompt** | In natural language | The LLM agent manages population dynamics through prompt instructions alone |
| **GEAR-Fixed** | Externalized, immutable code | A deterministic controller handles parent selection, operator scheduling, and promotion |
| **GEAR-Evolve** | Externalized, mutable code | The controller itself becomes part of the search and can be modified by the agent |

### Key Results (100 experiments, single H100, 5 min/experiment)

| Variant | Best bpb ↓ | VRAM (GB) | Params (M) | First exp. to beat Baseline |
|---|---|---|---|---|
| Baseline (AutoResearch) | 0.98232 | 60.2 | 80.9 | — |
| GEAR-Prompt | 0.98001 | 63.6 | 71.3 | 72 |
| GEAR-Fixed | 0.97914 | 66.2 | 85.9 | 84 |
| GEAR-Evolve | **0.97658** | **33.5** | 85.9 | **40** |

The baseline plateaus after ~50 experiments with zero improvement in the second half. All GEAR variants sustain improvement throughout the full budget.

## How It Works

This repo is a fork of [karpathy/autoresearch](https://github.com/karpathy/autoresearch). The core experimental setup is identical: a single editable `train.py`, a fixed 5-minute training budget per experiment, and validation bpb as the scalar objective.

GEAR replaces the keep-or-discard loop with a genetic search policy:

1. **Frontier maintenance** — A bounded population of elite nodes, each tagged with a role: `BEST` (lowest bpb), `LEAN` (lowest memory), or `DIVERSE` (materially different approach).
2. **Parent selection** — A composite score trading off productivity (UCB-style), local novelty (Jaccard distance), global coverage, and recency.
3. **Child creation** — Mutation (edit from one parent) or crossover (transplant an idea from a complementary second parent).
4. **Promotion** — Children enter the frontier if they set a new global best, improve on the weakest elite, offer a leaner configuration, or represent a sufficiently distinct line of investigation.

The `program.md` file encodes the search policy instructions for each variant.

## Project Structure

```
prepare.py        — constants, data prep + runtime utilities (do not modify)
train.py          — model, optimizer, training loop (agent modifies this)
program.md        — agent instructions / search policy
analysis.ipynb    — analysis and plotting of experiment results
pyproject.toml    — dependencies
```

## Quick Start

**Requirements:** A single NVIDIA GPU (tested on H100), Python 3.10+, [uv](https://docs.astral.sh/uv/).

```bash
# 1. Install uv project manager (if you don't already have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies
uv sync

# 3. Download data and train tokenizer (one-time, ~2 min)
uv run prepare.py

# 4. Manually run a single training experiment (~5 min)
uv run train.py
```

## Running the Agent

Point your Claude or coding agent at this repo (with permissions disabled), then prompt something like:

```
Hi, have a look at program.md and let's kick off a new experiment! Let's do the setup first.
```

The `program.md` file contains the full search policy. To switch GEAR variants, swap in the corresponding `program.md`:

- **GEAR-Prompt**: Search policy described in natural language within `program.md`
- **GEAR-Fixed**: Search policy externalized into a deterministic controller module
- **GEAR-Evolve**: Same as Fixed, but the agent is permitted to modify the controller code

## Design Choices

- **Single file to modify.** The agent only touches `train.py`. This keeps the scope manageable and diffs reviewable.
- **Fixed time budget.** Training always runs for exactly 5 minutes wall clock. This makes experiments directly comparable regardless of what the agent changes (model size, batch size, architecture, etc.).
- **Population-based search.** Instead of keeping only the best, GEAR maintains a frontier of elite states with distinct roles, enabling compositional gains via staged exploration across branches.
- **Mutation + crossover.** Mutation explores locally within each branch; crossover composes discoveries across branches, turning separate partial wins into stronger children.

## Citation

If you find this work useful, please cite:

```bibtex
@misc{jeddi2026geargeneticautoresearchagentic,
      title={GEAR: Genetic AutoResearch for Agentic Code Evolution},
      author={Ahmadreza Jeddi and Minh Ngoc Le and Hakki C. Karaimer and Konstantinos G. Derpanis and Babak Taati},
      year={2026},
      eprint={2605.13874},
      archivePrefix={arXiv},
      primaryClass={cs.NE},
      url={https://arxiv.org/abs/2605.13874},
}
```

## Acknowledgements

This project builds on [AutoResearch](https://github.com/karpathy/autoresearch) by Andrej Karpathy, which provides the base experimental setup and training infrastructure.

## License

MIT
