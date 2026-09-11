# Example session — conjecture under attack

**User:** I think x³ − 2x + 1 ≥ 0 for all x in [−2, 2]. Prove it or break it.

**Harness (plan):** formulate as universal claim → counterexample search
(symbolic → grid → random → adversarial) → verdict.

**Tool calls:**
1. `counterexample{predicate: x^3-2*x+1, bounds: {x: [-2,2]}, …}` →
   `{"status": "refuted", "counterexample": {"x": -2.0}, "predicate_value": -3.0}`

**Result:** `REFUTED` with a validated witness (x = −2, f = −3). The session
then suggests the true statement (roots near −1.618, 0.618, 1.0 — findable via
the `symbolic` solve op) instead of the false one. Runnable:
`demos/demo4_counterexample.py`.
