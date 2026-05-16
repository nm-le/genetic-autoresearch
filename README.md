# GEAR-Evolve

**GEAR variant where the agent can modify the genetic search controller itself, evolving the search policy during a run.**

This is one of three GEAR variants. See the [main README](../../tree/master) for an overview of the full project, and the [paper](https://arxiv.org/abs/2605.13874) and [project page](https://genetic-autoresearch.github.io/) for details.

## How GEAR-Evolve works

GEAR-Evolve starts from the same programmatic controller as GEAR-Fixed, but treats the controller as a **mutable search target**. The agent can edit both `train.py` (the experiment) and `controller.py` (the search policy), allowing it to repair failure modes and improve the search loop mid-run.

In practice, GEAR-Evolve:
- Detects when crossover suggestions become redundant or degenerate
- Patches the controller to restore complementarity constraints
- Adjusts selection and scheduling logic based on observed frontier dynamics

This makes GEAR-Evolve the strongest variant overall, reaching the lowest validation bpb and crossing the baseline plateau earliest.

### Result

| Variant | Best bpb ↓ | First exp. to beat Baseline |
|---|---|---|
| Baseline | 0.98232 | — |
| GEAR-Prompt | 0.98001 | 72 |
| GEAR-Fixed | 0.97914 | 84 |
| **GEAR-Evolve** | **0.97658** | **40** |

## Project structure

```
prepare.py       — constants, data prep, runtime utilities (do not modify)
train.py         — model, optimizer, training loop (agent modifies this)
controller.py    — genetic search controller (agent modifies this too)
program.md       — agent instructions (references the controller)
analysis.ipynb   — experiment analysis and plotting
pyproject.toml   — dependencies
```

## Quick start

```bash
git clone https://github.com/nm-le/genetic-autoresearch.git
cd genetic-autoresearch
git checkout gear-evolve

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
