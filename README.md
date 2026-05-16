# GEAR 🧬: Genetic AutoResearch for Agentic Code Evolution

[![arXiv](https://img.shields.io/badge/arXiv-2605.13874-b31b1b.svg)](https://arxiv.org/abs/2605.13874)
[![Project Page](https://img.shields.io/badge/Project-Page-blue)](https://genetic-autoresearch.github.io/)

> **GEAR** is a drop-in genetic search controller for [AutoResearch](https://github.com/karpathy/autoresearch)-style systems. It replaces single-incumbent hill climbing with a population-based frontier search over research states — maintaining multiple elite directions, recombining complementary ideas via crossover, and continuing to find improvements long after greedy search plateaus.

<p align="center">
  <img src="progress.png" width="700" alt="Running best validation bpb for Baseline vs GEAR variants over 100 experiments"/>
</p>

All three GEAR variants outperform the AutoResearch baseline under identical compute budgets (100 experiments, 5 min each on a single H100). The baseline stops improving after ~50 experiments; GEAR variants keep going.

| Variant | Best bpb ↓ | VRAM (GB) | Params (M) | First exp. to beat Baseline |
|---|---|---|---|---|
| Baseline (AutoResearch) | 0.98232 | 60.2 | 80.9 | — |
| GEAR-Prompt | 0.98001 | 63.6 | 71.3 | 72 |
| GEAR-Fixed | 0.97914 | 66.2 | 85.9 | 84 |
| GEAR-Evolve | **0.97658** | **33.5** | 85.9 | **40** |

## How it works

GEAR maintains a bounded frontier of elite nodes, each storing a code commit, measured metrics, parentage, and productivity statistics. At each step, the agent:

1. **Selects a parent** from the frontier, balancing productivity, novelty, coverage, and recency
2. **Spawns a child** via mutation (edit from one parent) or crossover (transplant an idea from a complementary second parent)
3. **Runs the experiment** under the fixed 5-minute training budget
4. **Promotes or discards** the child based on whether it earns a frontier slot (BEST, LEAN, or DIVERSE)

The frontier preserves partially successful ideas and complementary directions that a single-incumbent system would throw away.

## Three variants

Each variant shares the same experimental setup (identical to AutoResearch) but differs in how the genetic search policy is implemented:

| Variant | Branch | Search policy lives in... | Description |
|---|---|---|---|
| **GEAR-Prompt** | [`gear-prompt`](../../tree/gear-prompt) | Natural language instructions | The agent interprets population dynamics, parent selection, and promotion rules from prose in `program.md`. |
| **GEAR-Fixed** | [`gear-fixed`](../../tree/gear-fixed) | A fixed programmatic controller | Parent selection (UCB-style composite scoring), operator scheduling, and promotion are externalized into deterministic code the agent cannot modify. |
| **GEAR-Evolve** | [`gear-evolve`](../../tree/gear-evolve) | A mutable programmatic controller | Same as Fixed, but the agent can edit the controller itself — repairing failure modes and evolving the search policy over time. |

Each branch has its own README with variant-specific setup instructions and `program.md`.

## Quick start

**Requirements:** Single NVIDIA GPU (tested on H100), Python 3.10+, [uv](https://docs.astral.sh/uv/).

```bash
# Clone and switch to the variant you want to run
git clone https://github.com/nm-le/genetic-autoresearch.git
cd genetic-autoresearch
git checkout gear-evolve  # or gear-prompt, gear-fixed

# Install dependencies
uv sync

# One-time data prep (~2 min)
uv run prepare.py

# (Optional) Verify with a manual training run (~5 min)
uv run train.py
```

Then point your agent (Claude, Codex, etc.) at `program.md` and let it go:

```
Hi, have a look at program.md and let's kick off a new experiment! Let's do the setup first.
```

See each branch's README for variant-specific details.

## Project structure

```
prepare.py       — constants, data prep, runtime utilities (do not modify)
train.py         — model, optimizer, training loop (agent modifies this)
program.md       — agent instructions & search policy (variant-specific)
analysis.ipynb   — experiment analysis and plotting
pyproject.toml   — dependencies
```

## Key design choices

- **Same environment as AutoResearch.** Fixed 5-minute training budget, same data pipeline/tokenizer/evaluator, same `train.py` starting point. GEAR only changes the outer search loop.
- **Drop-in replacement.** No changes to the training harness or evaluation. Swap `program.md` (and the controller, for Fixed/Evolve) and everything else stays the same.
- **Population size P=4.** The frontier is deliberately small — enough to maintain distinct research directions (BEST, LEAN, DIVERSE) without diluting compute across too many branches.

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

## Acknowledgements

GEAR builds on [AutoResearch](https://github.com/karpathy/autoresearch) by Andrej Karpathy. The training code is a single-GPU implementation of [nanochat](https://github.com/karpathy/nanochat).

## License

MIT
