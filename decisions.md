# Decision log

Each loop iteration appends one line in the format:

`<ISO timestamp> | next exp_id: <id> | choice: <experiment|controller> | reason: <one sentence>`

2026-04-30T23:14:45Z | next exp_id: exp0001 | choice: experiment | reason: did not consider controller step — this is the first experiment, need baseline signal first
2026-04-30T23:24:59Z | next exp_id: exp0002 | choice: experiment | reason: did not consider controller step — only 1 experiment so far, need baseline signal first
2026-04-30T23:32:48Z | next exp_id: exp0003 | choice: controller | reason: degenerate crossover suggested — primary=elite/1 with secondary forced to baseline elite/0 because no other non-baseline parents exist; choose_operator should gate crossover on >=2 non-baseline elites
2026-04-30T23:34:26Z | next exp_id: exp0003 | choice: experiment | reason: considered controller step; just made one — re-suggest now produces mutate from elite/1 which is non-degenerate, proceed with experiment
2026-04-30T23:42:21Z | next exp_id: exp0004 | choice: controller | reason: degenerate crossover again — primary=elite/2 with secondary=elite/1, but elite/2 was a direct mutate-child of elite/1 (parent1=80d458b), so elite/1 carries no idea elite/2 doesn't already have; choose_operator should require >=2 lineage-independent non-baseline elites
2026-04-30T23:45:19Z | next exp_id: exp0004 | choice: experiment | reason: considered controller step; just made one — re-suggest now produces mutate from elite/2 which is non-degenerate, proceed with experiment
2026-04-30T23:52:23Z | next exp_id: exp0005 | choice: experiment | reason: considered controller step; rejected because the suggestion is non-degenerate (crossover baseline+depth9 yields a novel depth=8+warmdown=0.3 combination) and the search has only been running 4 experiments
2026-05-01T00:02:50Z | next exp_id: exp0006 | choice: controller | reason: suggested crossover(elite/1=depth=9, elite/2=warmdown=0.3) would recreate exp0003 (same depth=9+warmdown=0.3 recipe); root pathology is select_primary keeps picking known-bad elites — add quality-gap penalty
2026-05-01T00:07:14Z | next exp_id: exp0006 | choice: experiment | reason: considered controller step; just made one — re-suggest now produces crossover(elite/0, elite/3) which transplants MATRIX_LR=0.05 onto baseline, a non-duplicate non-degenerate combination
2026-05-01T00:14:11Z | next exp_id: exp0007 | choice: experiment | reason: considered controller step; rejected because exp0006 just produced a new global best (search is now healthy and productive)
2026-05-01T00:21:15Z | next exp_id: exp0008 | choice: experiment | reason: considered controller step; rejected because last 2 experiments produced new global bests and the crossover suggestion is a fresh combination (depth=9 + MATRIX_LR=0.06) not a duplicate
2026-05-01T00:28:20Z | next exp_id: exp0009 | choice: experiment | reason: considered controller step; rejected because the MATRIX_LR sweep on depth=8 has produced 2 new bests (search healthy), continue
2026-05-01T00:35:21Z | next exp_id: exp0010 | choice: experiment | reason: considered controller step; rejected because suggestion is a fresh combination (depth=8 + MATRIX_LR=0.06 + WARMDOWN=0.3), not a duplicate, search still healthy
2026-05-01T00:42:59Z | next exp_id: exp0011 | choice: experiment | reason: considered controller step; rejected because elite/2 is only 0.0026 worse than best (not a known-bad parent) and we have not over-stretched the controller-change budget
2026-05-01T00:49:48Z | next exp_id: exp0012 | choice: experiment | reason: considered controller step; rejected because suggestion is fresh combination (MATRIX_LR=0.07 + EMBEDDING_LR=0.5), not a duplicate
2026-05-01T00:56:47Z | next exp_id: exp0013 | choice: experiment | reason: considered controller step; rejected because elite/3 mutation produces a useful test of EMBEDDING_LR=0.5 in the MATRIX_LR=0.06+warmdown=0.3 region; search still healthy
2026-05-01T01:03:35Z | next exp_id: exp0014 | choice: experiment | reason: considered controller step; rejected because suggestion is exactly the high-priority test from exp0012's reflection (EMBEDDING_LR=0.5 onto MATRIX_LR=0.06 base)
2026-05-01T01:10:32Z | next exp_id: exp0015 | choice: experiment | reason: considered controller step; rejected because mutating elite/1 (MATRIX_LR=0.07+EMBEDDING_LR=0.5) toward MATRIX_LR=0.065 is a clean 1D fine-tune sweep
2026-05-01T04:22:21Z | next exp_id: exp0016 | choice: experiment | reason: considered controller step; rejected because crossover suggestion is a fresh combination (MATRIX_LR=0.065+warmdown=0.3) not yet tested
2026-05-01T04:29:28Z | next exp_id: exp0017 | choice: experiment | reason: considered controller step; rejected because mutating elite/2 with a fresh untouched knob (WEIGHT_DECAY) opens a new search axis
2026-05-01T04:36:50Z | next exp_id: exp0018 | choice: experiment | reason: considered controller step; rejected because suggestion is a fresh untested 5-knob combination, even though warmdown=0.3 has been worse historically — taking the bet
2026-05-01T04:43:52Z | next exp_id: exp0019 | choice: experiment | reason: considered controller step; rejected because last experiment produced new global best — search healthy, continue WEIGHT_DECAY sweep
2026-05-01T04:51:50Z | next exp_id: exp0020 | choice: controller | reason: suggested crossover(elite/0, elite/2) is degenerate — elite/2 is a deep conceptual ancestor of elite/0 (chain: b26413d → c57cda9 → 451f99b), so its EMBEDDING_LR=0.5 idea is already in the base; current _lineage_independent only checks direct parent1
2026-05-01T04:54:12Z | next exp_id: exp0020 | choice: experiment | reason: considered controller step; just made one — re-suggest now produces non-degenerate crossover(elite/0, elite/1) with fresh combination (MATRIX_LR=0.065+WD=0.10+EMB=0.5)
2026-05-01T05:01:17Z | next exp_id: exp0021 | choice: experiment | reason: considered controller step; rejected — search productive, continue WEIGHT_DECAY sweep
2026-05-01T05:09:08Z | next exp_id: exp0022 | choice: controller | reason: suggested crossover(elite/0,elite/1) repeats the pair used in exp0020 — only one lineage-independent secondary exists, and pair_penalty is too weak to prevent re-suggestion; need untried-pair gate
2026-05-01T05:11:03Z | next exp_id: exp0022 | choice: experiment | reason: considered controller step; just made one — re-suggest now produces mutate from elite/0 which is non-degenerate
2026-05-01T05:18:06Z | next exp_id: exp0023 | choice: experiment | reason: considered controller step; rejected because suggestion is a fresh untried pair (elite/2,elite/3) producing untested combo MATRIX_LR=0.065+WD=0.05+EMB=0.5
2026-05-01T05:25:11Z | next exp_id: exp0024 | choice: experiment | reason: considered controller step; rejected because mutating elite/1 with ADAM_BETAS opens a fresh untouched optimization axis
2026-05-01T05:32:04Z | next exp_id: exp0025 | choice: experiment | reason: considered controller step; rejected because WARMDOWN sweep in untested direction (0.5->0.6) is a clean 1D test
2026-05-01T05:39:04Z | next exp_id: exp0026 | choice: experiment | reason: considered controller step; rejected because untried pair (elite/3,elite/1) producing fresh combination
2026-05-01T05:45:58Z | next exp_id: exp0027 | choice: experiment | reason: considered controller step; rejected because mutating elite/2 with SCALAR_LR opens an untouched axis
2026-05-01T05:52:49Z | next exp_id: exp0028 | choice: experiment | reason: considered controller step; rejected because mutating elite/0 with untouched UNEMBEDDING_LR axis is high-value
2026-05-01T05:59:39Z | next exp_id: exp0029 | choice: experiment | reason: considered controller step; rejected because continuing WARMDOWN sweep direction (0.6->0.7) is a clean 1D test
2026-05-01T06:06:40Z | next exp_id: exp0030 | choice: experiment | reason: considered controller step; rejected because mutating elite/3 with untouched TOTAL_BATCH_SIZE axis is high-value; search still healthy, controller producing fresh suggestions
2026-05-01T06:13:45Z | next exp_id: exp0031 | choice: experiment | reason: considered controller step; rejected because exp0030 just produced massive new best — search very healthy, follow-up crossover is fresh combination
2026-05-01T06:20:51Z | next exp_id: exp0032 | choice: experiment | reason: considered controller step; rejected because two consecutive new bests — search extremely healthy, continue exploring TOTAL_BATCH=2**18 regime
2026-05-01T06:27:38Z | next exp_id: exp0033 | choice: experiment | reason: considered controller step; rejected because three consecutive new bests — search extremely productive
2026-05-01T06:34:37Z | next exp_id: exp0034 | choice: experiment | reason: considered controller step; rejected because doubling-down on the productive batch-size direction is a clean single-idea mutation (needs both TOTAL_BATCH and DEVICE_BATCH due to integer constraint)
2026-05-01T06:41:48Z | next exp_id: exp0035 | choice: experiment | reason: considered controller step; rejected — fresh combination, search highly productive
2026-05-01T06:48:44Z | next exp_id: exp0036 | choice: experiment | reason: considered controller step; rejected — continuing the productive smaller-batch direction
2026-05-01T06:57:06Z | next exp_id: exp0037 | choice: controller | reason: suggested crossover(elite/0,elite/1) is no-op — elite/1's warmdown=0.6 idea is already in elite/0 via parent2 chain (dbbdc5a → 0b91c83 → c1c146d=elite/1); _conceptual_ancestors only walks parent1
2026-05-01T06:58:24Z | next exp_id: exp0037 | choice: experiment | reason: considered controller step; just made one — re-suggest now produces mutate from elite/0
2026-05-01T07:05:37Z | next exp_id: exp0038 | choice: experiment | reason: considered controller step; rejected — search just produced massive new best, continue scaling depth
2026-05-01T07:12:44Z | next exp_id: exp0039 | choice: experiment | reason: considered controller step; rejected — depth scaling productive, continue
2026-05-01T07:20:10Z | next exp_id: exp0040 | choice: experiment | reason: considered controller step; rejected — re-tuning MATRIX_LR for bigger DEPTH=10 model
2026-05-01T07:26:59Z | next exp_id: exp0041 | choice: experiment | reason: considered controller step; rejected — fresh untried combination DEPTH=11+MATRIX_LR=0.05
2026-05-01T07:33:55Z | next exp_id: exp0042 | choice: experiment | reason: considered controller step; rejected — continuing productive MATRIX_LR sweep at DEPTH=10
2026-05-01T07:41:00Z | next exp_id: exp0043 | choice: experiment | reason: considered controller step; rejected — fresh combination (DEPTH=11 + MATRIX_LR=0.045) not previously tried
2026-05-01T07:48:05Z | next exp_id: exp0044 | choice: experiment | reason: considered controller step; rejected — continuing productive MATRIX_LR sweep
2026-05-01T07:55:39Z | next exp_id: exp0045 | choice: experiment | reason: considered controller step; rejected — controller-fix budget exhausted recently, will run the suggested duplicate to confirm reproducibility
2026-05-01T08:02:55Z | next exp_id: exp0046 | choice: experiment | reason: considered controller step; rejected — mutating elite/3 (DEPTH=11) with ASPECT_RATIO change opens a fresh sub-region (DEPTH=11 + narrower)
2026-05-01T14:04:22Z | next exp_id: exp0047 | choice: experiment | reason: considered controller step; rejected — testing WD sweep from elite/2 base (untouched WD at this MATRIX_LR=0.04 + DEPTH=10 + small-batch combination)
2026-05-01T14:11:17Z | next exp_id: exp0048 | choice: experiment | reason: considered controller step; rejected — fresh untried pair, fresh combo
2026-05-01T14:18:25Z | next exp_id: exp0049 | choice: experiment | reason: considered controller step; rejected — testing WD upward direction at current best base
2026-05-01T14:25:20Z | next exp_id: exp0050 | choice: experiment | reason: considered controller step; rejected — fresh combo WD=0.075+MATRIX_LR=0.04
2026-05-01T14:32:15Z | next exp_id: exp0051 | choice: experiment | reason: considered controller step; rejected — testing untouched HEAD_DIM axis at best base
2026-05-01T14:39:21Z | next exp_id: exp0052 | choice: experiment | reason: considered controller step; rejected — testing WINDOW_PATTERN axis at best base
2026-05-01T14:46:24Z | next exp_id: exp0053 | choice: experiment | reason: considered controller step; rejected — fresh untried combo
2026-05-01T14:53:23Z | next exp_id: exp0054 | choice: experiment | reason: considered controller step; rejected — testing ADAM_BETAS at best base
2026-05-01T15:00:03Z | next exp_id: exp0055 | choice: experiment | reason: considered controller step; rejected — fresh combo
2026-05-01T15:06:58Z | next exp_id: exp0056 | choice: experiment | reason: considered controller step; rejected — testing wider model (ASPECT_RATIO 64->72)
2026-05-01T15:14:29Z | next exp_id: exp0057 | choice: experiment | reason: considered controller step; rejected — testing Muon momentum schedule (untouched axis)
2026-05-01T15:21:35Z | next exp_id: exp0058 | choice: experiment | reason: considered controller step; rejected — search at plateau, exploring WD upper sweep at SSLL base
2026-05-01T15:28:34Z | next exp_id: exp0059 | choice: experiment | reason: considered controller step; rejected — testing ADAM_BETAS (0.85, 0.99) untested combo
2026-05-01T15:35:21Z | next exp_id: exp0060 | choice: experiment | reason: considered controller step; rejected — testing softcap (untouched code-level knob)
2026-05-01T15:42:40Z | next exp_id: exp0061 | choice: experiment | reason: considered controller step; rejected — fresh combo softcap=10 + WINDOW=SSLL
2026-05-01T15:49:42Z | next exp_id: exp0062 | choice: experiment | reason: considered controller step; rejected — productive softcap sweep direction
2026-05-01T15:56:45Z | next exp_id: exp0063 | choice: experiment | reason: considered controller step; rejected — softcap fine-tune between 10 and 15
2026-05-01T16:04:04Z | next exp_id: exp0064 | choice: experiment | reason: considered controller step; rejected — testing ADAM_BETAS (0.9, 0.95)
2026-05-01T16:11:09Z | next exp_id: exp0065 | choice: experiment | reason: considered controller step; rejected — fine-tune MATRIX_LR
2026-05-01T16:18:04Z | next exp_id: exp0066 | choice: experiment | reason: considered controller step; rejected — fresh combo MATRIX_LR=0.0425 + SSLL
2026-05-01T16:24:54Z | next exp_id: exp0067 | choice: experiment | reason: considered controller step; rejected — high-value test combining two productive directions
2026-05-01T16:31:46Z | next exp_id: exp0068 | choice: experiment | reason: considered controller step; rejected — fine WD sweep at new peak base
2026-05-01T16:38:41Z | next exp_id: exp0069 | choice: experiment | reason: considered controller step; rejected — search just got new best, continue
2026-05-01T16:45:24Z | next exp_id: exp0070 | choice: experiment | reason: considered controller step; rejected — continuing productive WD sweep
2026-05-01T16:52:30Z | next exp_id: exp0071 | choice: experiment | reason: considered controller step; rejected — likely duplicate of exp0069, but lineage check passes; accept
2026-05-01T16:59:29Z | next exp_id: exp0072 | choice: experiment | reason: considered controller step; rejected — fine EMB_LR sweep at elite/0
2026-05-01T17:06:20Z | next exp_id: exp0073 | choice: experiment | reason: considered controller step; rejected — fine WD sweep on SSLL variant
2026-05-01T17:13:17Z | next exp_id: exp0074 | choice: experiment | reason: considered controller step; rejected — testing untouched x0_lambdas init
2026-05-01T17:20:20Z | next exp_id: exp0075 | choice: experiment | reason: considered controller step; rejected — search just got new best, continue
2026-05-01T17:27:02Z | next exp_id: exp0076 | choice: experiment | reason: considered controller step; rejected — productive x0_lambdas sweep
2026-05-01T17:33:49Z | next exp_id: exp0077 | choice: experiment | reason: considered controller step; rejected — fresh combo with new x0_lambdas base
2026-05-01T17:40:34Z | next exp_id: exp0078 | choice: experiment | reason: considered controller step; rejected — testing untouched rotary base
2026-05-01T17:47:31Z | next exp_id: exp0079 | choice: experiment | reason: considered controller step; rejected — likely no-op crossover (both have SSLL), but accepting for variance check
2026-05-01T17:54:28Z | next exp_id: exp0080 | choice: experiment | reason: considered controller step; rejected — continue rotary direction (50000 -> 100000)
2026-05-01T18:01:15Z | next exp_id: exp0081 | choice: experiment | reason: considered controller step; rejected — fresh combo
2026-05-01T18:08:06Z | next exp_id: exp0082 | choice: experiment | reason: considered controller step; rejected — fine rotary base sweep
2026-05-01T18:14:52Z | next exp_id: exp0083 | choice: experiment | reason: considered controller step; rejected — fresh combo
2026-05-01T18:21:31Z | next exp_id: exp0084 | choice: experiment | reason: considered controller step; rejected — productive rotary direction
2026-05-01T18:28:15Z | next exp_id: exp0085 | choice: experiment | reason: considered controller step; rejected — combine SSSL + rotary=30000 + x0_lambdas=0.05
2026-05-01T18:35:05Z | next exp_id: exp0086 | choice: experiment | reason: considered controller step; rejected — fresh combo (sub-optimal but follow)
2026-05-01T18:41:49Z | next exp_id: exp0087 | choice: experiment | reason: considered controller step; rejected — fine-tune rotary near peak
2026-05-01T18:48:38Z | next exp_id: exp0088 | choice: experiment | reason: considered controller step; rejected — sub-optimal but follow
2026-05-01T18:55:30Z | next exp_id: exp0089 | choice: experiment | reason: considered controller step; rejected — testing MATRIX_LR sweep at sub-optimal x0 base
2026-05-01T19:02:17Z | next exp_id: exp0090 | choice: experiment | reason: considered controller step; rejected — fresh untried combo SSSL+rotary=30000+x0=0.025
2026-05-01T19:09:07Z | next exp_id: exp0091 | choice: experiment | reason: considered controller step; rejected — MATRIX_LR sweep from elite/2 (sub-optimal rotary base)
2026-05-01T19:15:57Z | next exp_id: exp0092 | choice: experiment | reason: considered controller step; rejected — combine x0=0.05 with MATRIX_LR=0.05
2026-05-01T19:22:48Z | next exp_id: exp0093 | choice: experiment | reason: considered controller step; rejected — fresh combo
2026-05-01T19:29:32Z | next exp_id: exp0094 | choice: experiment | reason: considered controller step; rejected — productive MATRIX_LR direction
2026-05-01T19:36:22Z | next exp_id: exp0095 | choice: experiment | reason: considered controller step; rejected — fine-tune x0 upper sweep
2026-05-01T19:43:26Z | next exp_id: exp0096 | choice: experiment | reason: considered controller step; rejected — fresh EMB_LR sweep
2026-05-01T19:50:32Z | next exp_id: exp0097 | choice: experiment | reason: considered controller step; rejected — fine WD sweep at MATRIX_LR=0.05 base
2026-05-01T19:57:38Z | next exp_id: exp0098 | choice: experiment | reason: considered controller step; rejected — likely no-op (same x0) but follow
2026-05-01T20:04:37Z | next exp_id: exp0099 | choice: experiment | reason: considered controller step; rejected — combine x0=0.05 with WD=0.05 base
2026-05-01T20:11:32Z | next exp_id: exp0100 | choice: experiment | reason: considered controller step; rejected — sub-optimal but follow
2026-05-01T20:18:24Z | next exp_id: exp0101 | choice: experiment | reason: considered controller step; rejected — fine UNEMB_LR sweep at new best
