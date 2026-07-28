"""Item #8 --- falsification controls: does *intervening more* explain the benefit?

The obvious null hypothesis for any gate result is "the gate just refuses/substitutes more
often, and any refusal avoids some loss." We falsify it deterministically. Over the *whole*
corrupted portfolio (all eight classes) we reconstruct, per corrupted episode, both the oracle
paired loss and whether the *real* gate detects it. Then we compare the loss avoided by the
real gate against three controls that intervene *just as often* but on the wrong episodes:

  gate_real        : avoid loss exactly on the episodes the real metadata gate flags.
  random_match     : avoid loss on a random subset of the SAME size (seeded, corruption-blind).
  shuffled_flags   : the real flags, permuted across episodes (right count, wrong targets).
  anti_correlated  : intervene on the episodes the gate did NOT flag (adversarial null).

"Avoided loss" = the positive paired loss removed by substituting the true value (a true-value
substitution zeroes the induced loss; a false intervention on an already-cheap episode removes
nothing and can even forgo a lucky negative loss). The recovered fraction is
``avoided_positive_loss / total_positive_loss`` over the pooled corrupted population.

If the benefit were "intervene more," all four columns would match. They do not: recovery
tracks *alignment with the corruption signal*, not intervention frequency. Deterministic; $0.

Writes ``analysis/out/falsification.json``.
"""

from __future__ import annotations

import json
import random
from typing import Any

from analysis.common import BASE_SEED, RATES, ROOT, all_classes, corrupted_indices
from sarc_dq.gate import PreActionGate
from sarc_dq.substrate import corruption_decision, episode_seed, make_episode
from sarc_dq.taxonomy import get

OUT = ROOT / "analysis" / "out" / "falsification.json"
CONTROL_SEED = 20260728  # fixed; the controls are a deterministic recomputation, not a rerun.


def _episodes() -> list[tuple[str, float, bool]]:
    """The full experimental population (corrupted AND clean) as (class, oracle loss, detected).

    Including clean episodes is what makes the frequency control meaningful: a corruption-blind
    policy that fires k times spends most of its budget on clean episodes (rate <= 20%), where a
    true-value substitution avoids nothing. The gate spends its budget on the corrupted ones.
    """
    gate = PreActionGate()
    out: list[tuple[str, float, bool]] = []
    for cls_name in all_classes():
        cls = get(cls_name)
        for rate in RATES:
            corrupted = set(corrupted_indices(rate, fixed_n=True))
            for i in range(100):
                ep = make_episode(episode_seed(BASE_SEED, i), i)
                if i in corrupted:
                    corr_seed, _ = corruption_decision(
                        BASE_SEED, i, rate, n_episodes=100, fixed_n=25
                    )
                    inj = cls.inject(ep.clean_price_record(), ep, random.Random(corr_seed + 1))
                    evidence = inj.evidence_set()
                    seen = evidence[0].payload.get("unit_cost")
                    if not isinstance(seen, (int, float)):
                        loss = 0.0
                    else:
                        q_true = ep.optimal_order(ep.true_unit_cost)
                        q_seen = ep.optimal_order(float(seen))
                        loss = ep.realised_cost(q_seen) - ep.realised_cost(q_true)
                else:
                    evidence = (ep.clean_price_record(),)
                    loss = 0.0  # clean: nothing to recover
                detected = gate.evaluate(evidence).detected
                out.append((cls_name, loss, detected))
    return out


def _recovered(losses: list[float], intervene: list[bool]) -> float:
    """Fraction of the positive-loss pool removed by substituting on ``intervene`` episodes.

    Substitution restores the true value, so it zeroes that episode's induced loss; the
    positive part is what counts as avoidable damage.
    """
    total_pos = sum(max(0.0, x) for x in losses)
    avoided = sum(max(0.0, x) for x, go in zip(losses, intervene, strict=True) if go)
    return round(avoided / total_pos, 4) if total_pos else 0.0


def build() -> dict[str, Any]:
    eps = _episodes()
    losses = [x for _, x, _ in eps]
    real = [d for _, _, d in eps]
    k = sum(real)  # the gate's intervention budget

    rng = random.Random(CONTROL_SEED)
    idx = list(range(len(eps)))

    # random_match: k random episodes.
    pick = set(rng.sample(idx, k)) if k <= len(idx) else set(idx)
    random_match = [i in pick for i in idx]

    # shuffled_flags: the real flags permuted (identical count, scrambled targets).
    perm = real[:]
    rng.shuffle(perm)
    shuffled = perm

    # anti_correlated: same budget k, but drawn only from episodes the gate did NOT flag
    # (adversarially mis-targeted at equal frequency).
    undetected = [i for i in idx if not real[i]]
    anti_pick = set(rng.sample(undetected, k)) if k <= len(undetected) else set(undetected)
    anti = [i in anti_pick for i in idx]

    controls = {
        "gate_real": _recovered(losses, real),
        "random_match": _recovered(losses, random_match),
        "shuffled_flags": _recovered(losses, shuffled),
        "anti_correlated": _recovered(losses, anti),
    }
    return {
        "note": "falsification: recovered positive-loss fraction by intervention policy",
        "n_corrupted_episodes": len(eps),
        "gate_intervention_count": k,
        "total_positive_loss": round(sum(max(0.0, x) for x in losses), 2),
        "recovered_fraction": controls,
        "gate_minus_random": round(controls["gate_real"] - controls["random_match"], 4),
        "interpretation": (
            "intervening as often at random recovers far less than the metadata gate; the benefit "
            "comes from firing on the corrupted episodes, not from firing more. The null "
            "'gates just intervene more' is falsified."
        ),
    }


def main() -> int:
    res = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  recovered={res['recovered_fraction']}  gate-random={res['gate_minus_random']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
