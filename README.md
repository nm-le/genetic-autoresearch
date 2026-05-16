# GEAR-Prompt

**GEAR variant where the genetic search policy lives entirely in natural language instructions.**

This is one of three GEAR variants. See the [main README](../../tree/master) for an overview of the full project, and the [paper](https://arxiv.org/abs/2605.13874) and [project page](https://genetic-autoresearch.github.io/) for details.

## How GEAR-Prompt works

GEAR-Prompt is the minimal-intervention variant. The population frontier, parent selection, mutation/crossover logic, and promotion rules are all described as prose instructions in `program.md`. The agent interprets and executes these instructions at each experiment step.

There is no external controller code — the agent itself is responsible for:
- Maintaining the frontier state (tracking elites, parentage, and metrics)
- Deciding when to mutate vs. crossover
- Selecting parents based on the described scoring criteria
- Promoting or discarding children according to the frontier roles (BEST, LEAN, DIVERSE)

This makes GEAR-Prompt the easiest to set up and modify, but also the most sensitive to how the agent interprets instructions. In practice, prompt-only crossover tends to degenerate over time (reusing the same parent pairs, losing complementarity), which motivates the Fixed and Evolve variants.

### Result

| Variant | Best bpb ↓ |
|---|---|
| Baseline | 0.98232 |
| **GEAR-Prompt** | **0.98001** |

## Project structure

```
prepare.py       — constants, data prep, runtime utilities (do not modify)
train.py         — model, optimizer, training loop (agent modifies this)
program.md       — agent instructions including genetic search policy
analysis.ipynb   — experiment analysis and plotting
pyproject.toml   — dependencies
```

## Quick start

```bash
git clone https://github.com/nm-le/genetic-autoresearch.git
cd genetic-autoresearch
git checkout gear-prompt

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
