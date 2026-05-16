# GEAR-Fixed

**GEAR variant where the genetic search policy is externalized as a deterministic programmatic controller.**

This is one of three GEAR variants. See the [main README](../../tree/master) for an overview of the full project, and the [paper](https://arxiv.org/abs/2605.13874) and [project page](https://genetic-autoresearch.github.io/) for details.

## How GEAR-Fixed works

GEAR-Fixed separates *what the agent changes* (the experiment code in `train.py`) from *how the agent searches* (the controller). The search policy — parent selection, operator scheduling, promotion logic — is implemented as deterministic code that the agent calls but **cannot modify**.

The controller handles:
- **Parent selection** via a UCB-style composite score balancing productivity, novelty, coverage, and recency
- **Operator scheduling** to decide mutation vs. crossover and enforce complementarity between crossover parents
- **Frontier promotion** with explicit role assignments (BEST, LEAN, DIVERSE)

By externalizing these decisions into code, GEAR-Fixed avoids the failure modes of prompt-only execution (degenerate crossover, drifting selection criteria) while keeping the search policy frozen and auditable.

### Result

| Variant | Best bpb ↓ |
|---|---|
| Baseline | 0.98232 |
| GEAR-Prompt | 0.98001 |
| **GEAR-Fixed** | **0.97914** |

## Project structure

```
prepare.py       — constants, data prep, runtime utilities (do not modify)
train.py         — model, optimizer, training loop (agent modifies this)
controller.py    — genetic search controller (agent calls but does NOT modify)
program.md       — agent instructions (references the controller)
analysis.ipynb   — experiment analysis and plotting
pyproject.toml   — dependencies
```

## Quick start

```bash
git clone https://github.com/nm-le/genetic-autoresearch.git
cd genetic-autoresearch
git checkout gear-fixed

uv sync
uv run prepare.py    # one-time data prep
uv run train.py      # optional: verify setup

# Then point your agent at program.md
```

**Requirements:** Single NVIDIA GPU (tested on H100), Python 3.10+, [uv](https://docs.astral.sh/uv/).

## Citation

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
