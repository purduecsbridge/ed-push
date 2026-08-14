# Verify before reporting "done"

"I checked and it's fine" and "I re-ran it and it's fine" are
different claims. Only the second one is safe to report as fact,
whether it's a subagent reporting to you or you reporting to the user.

## What actually happened on the livecodingexam port

(2026-08-13, porting the 5-problem Live Coding Exam to Ed — see
`livecodingexam/problem1-hotel` through `problem5-armstrong/ed/`.)

The `ed-porter` subagent's first pass reported all 5 graders fully
verified: "✓ Solution Verification", "✓ Points Reconciliation," etc.
Independently recompiling and running every grader — JUnit console
launcher, actual solution and actual scaffold, real pass/fail counts —
found two defects the summary had missed:

- A Queue test wrapped `Reflect.call(...)` in
  `assertThrows(NoSuchElementException.class, ...)`. `Reflect.call()`
  catches the underlying `InvocationTargetException` internally and
  converts it into a JUnit `fail()` (an `AssertionFailedError`) before
  it can propagate — so `assertThrows` could never see the real
  exception type. The *reference solution* was failing its own test.
- An Armstrong test hardcoded the wrong expected boolean for one of
  its ten inputs (asserted `9800917` was an Armstrong number under the
  ported algorithm; it isn't — verifiable by hand in under a minute).

The agent's own prose summary that produced these claims even
contained an arithmetic error in a points breakdown that didn't sum to
the stated total — something addable on a napkin, that nobody had
added.

A second pass (adding `ed/verify/mutation-test.py` per
[[mutation-testing.md]]) came back clean on independent re-run — so
this isn't "the subagent's work is untrustworthy," it's that a report
of success and a demonstration of success are different objects, and
treating the first as the second is where defects slip through.

Later in the same port, a human (not any agent) reviewing the Queue
solution by eye found a third gap that had survived *both* the manual
solution/scaffold re-check *and* the mutation-testing audit — see the
worked example in [[mutation-testing.md]]. Verification catches what
it's specifically built to catch; a human reading the actual algorithm
is still a distinct, valuable check that automated re-runs don't
replace.

## How to apply this

For any Ed grader — freshly written, ported from an old harness, or
handed back by a subagent as "done" — before treating it as done:

1. Actually compile `testbase/` + `solution/` + `scaffold/`.
2. Actually run the suite against the solution. Read the real number:
   must be 100%. Don't accept "compiles cleanly" as a stand-in for
   "passes."
3. Actually run the suite against the untouched scaffold. Read the
   real number: must be 0%.
4. Run the `mutation-test.py` audit and read *that* real output too —
   every twin named as caught, not a summary that says "audited."
5. If a report (yours, a subagent's, anyone's) makes a specific
   numeric claim — points sum to X, N tests pass — the cheapest check
   available is to add the numbers yourself. Do that before repeating
   the claim.

None of this is about distrusting whoever did the work. It's that
"reported successful" and "verified successful" are different claims,
and a grader that silently under- or over-scores a real exam is
exactly the kind of failure that's invisible until a student hits it.
