# Mutation-testing a grader

Solution scores 100%, scaffold scores 0% — that's necessary, but it is
**not sufficient**. It proves the grader reacts to the two extremes
(everything right, nothing done). It says nothing about whether each
individual test actually verifies the behavior it claims to, versus
just happening to pass alongside a correct solution.

The only way to know a test discriminates is to break the thing it's
supposed to test, on purpose, and confirm the test catches it — and to
do this for every test, not just the ones that feel risky.

## The audit script

Write `ed/verify/mutation-test.py` for every grader (`ed/verify/` is
not one of the four filespaces `ed_push.py` uploads — scaffold,
solution, testbase, check — so it never reaches Ed; it's pure local
tooling). Three checks, in order:

1. **Points.** `@Tag("score:N")` values sum to exactly `points:`, and
   the reference solution sweeps every test.
2. **Scaffold.** The untouched scaffold scores 0 — no free points.
3. **Wrong twins.** A list of deliberately-broken copies of the
   reference solution, each a single targeted edit, each paired with
   the test that should catch it. Run every twin through the real
   grader. A twin that's caught by nothing is a test gap. A twin
   that's caught by the wrong test (or half the suite when only one
   test should fail) means the tests overlap more than intended, or a
   failure is cascading further than expected.

Reference implementation: `lab14/ed/verify/mutation-test.py` in the
CSbridge-TA repo (the original of this pattern), and the five
`livecodingexam/problem*/ed/verify/mutation-test.py` scripts for
worked examples across stdin/file-I/O, single-class reflection, and
multi-file/linked-structure graders. All compile-and-run the real
`testbase/` against a temp-staged twin via the JUnit console launcher,
parse the `✘`/`tests successful` output, and fail loudly (non-zero
exit) if any twin isn't caught as expected.

Run it for real — `python3 ed/verify/mutation-test.py` — and read the
actual per-twin output. A checklist that says "✓ mutation tested" in
prose is not the same claim as a script that just printed `AUDIT
PASSED` with every twin named.

## Twins have to be adversarial, not just present

A twin list that only ever breaks one line at a time can still miss a
gap that only shows up when a whole *branch* of behavior is silently
absent. Worked example, from the `livecodingexam` Queue port
(2026-08-13):

```java
public void add(String s) {
    MyNode node = new MyNode(s);
    if (this.front == null) {
        this.front = node;
    } else if (this.back == null) {
        this.front.next = node;   // links element #2
        this.back = node;
    } else {
        this.back.next = node;    // links element #3+
        this.back = this.back.next;
    }
}
```

The grader's multi-element tests (`add` three or four values, then
call `peek()`) only ever read `front`. Gutting *both* the `else if` and
`else` bodies — leaving only the first-element branch working — still
scored 100%, because nothing ever looked past the front node. Neither
a solution=100/scaffold=0 check nor the existing per-line twins caught
it, because none of them modeled "only the first branch of a
multi-branch method works, the rest are quietly no-ops."

Two things follow:

- **For any structure with distinct first/middle/last branches**
  (linked lists, queues, stacks, BSTs, anything built by repeated
  insertion), don't test multi-element behavior with a single-element
  read (`peek`, `getFirst`, `top`). **Drain or walk the whole
  structure** in the test — repeated `remove()`, an iterator, a
  `toString()` you actually call — so a broken middle/back branch has
  somewhere to be visible.
- **Add a twin that guts every branch except one**, not only twins
  that swap one branch for another. "Only the base case works" is a
  qualitatively different bug from "the base case and the recursive
  case are swapped," and needs its own twin.

## When a twin exposes a real gap

Don't weaken the twin to make the audit pass — strengthen the test.
Fix order:

1. Reproduce the twin against the *actual* committed grader first (not
   a hypothetical) — compile it, run it, confirm the failure is real.
2. Strengthen the test(s) that should have caught it.
3. Re-run solution=100/scaffold=0 to confirm the strengthening didn't
   break anything.
4. Re-run the twin against the strengthened grader — confirm it now
   fails, and fails via the test you expected.
5. Add the twin to the permanent list in `mutation-test.py` so the gap
   can't silently regress.
6. Re-run the *whole* audit (all twins, not just the new one) before
   calling it done.

See also [[grader-design.md]] for the scaffold-must-fail-everything
rule this extends, and [[verify-before-reporting.md]] for why step 1
(reproduce against the real committed code) matters even when you
wrote the fix yourself.
