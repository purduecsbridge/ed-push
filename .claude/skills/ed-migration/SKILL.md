---
name: ed-migration
description: Port CS Bridge labs, homework and bonus challenges to Ed (edstem.org) and re-publish them with ed_push.py. Use for anything touching challenge.yaml, writeup.md/handout.md authoring, scaffold/solution/testbase/check filespaces, JUnit graders with @Tag scoring, the ExamRunner/Reflect harness, Ed's markdown subset and runnable snippets, slide/lesson ids, or the Ed REST API's undocumented behaviour. Triggers on "push to Ed", "migrate a lab", "ed-push", "challenge.yaml", "Ed slide", "grader", "testbase".
---

# Ed migration

Everything needed to move a lab from a plain repo onto Ed and keep it
re-publishable from git. The repo directory is the source of truth;
`ed_push.py` is the only thing that talks to Ed.

## Ground rules

1. **Never run the real push. Hand back the command.** `--no-dry-run`
   hits a live course and is the user's call — not yours, even when
   asked to "just push it". Dry-runs are fine; they write nothing.
2. **The `ed/` directory is the source of truth.** Edit files → dry-run
   → push → read the ✓/✗ verify table. If any row is ✗, the challenge
   is not usable; fix and re-push.
3. **Never guess a slide or lesson id.** They are globally unique and
   they route the push. A wrong id silently overwrites someone else's
   slide. Read ids from the Ed URL or from a previous push's output.
4. **Points must reconcile.** `@Tag("score:N")` across the grader must
   sum to `points:` in `challenge.yaml`. Check it every time — this is
   the single most common silent defect.
5. **Verify locally before pushing.** Reference solution passes
   everything; untouched scaffold fails everything it should. Actually
   run it — a compile-clean claim is not a passing-tests claim.
6. **Mutation-test before calling a grader done.** Solution=100% and
   scaffold=0% proves the two extremes, not that each test
   discriminates. Write `ed/verify/mutation-test.py` per
   `references/mutation-testing.md` and read its real output.
7. **Verify, don't just report — yours or a subagent's.** "Checked and
   it's fine" and "re-ran it and it's fine" are different claims. See
   `references/verify-before-reporting.md` for what slipped through
   when this wasn't followed.

## The layout

```
some-lab/ed/
  challenge.yaml     manifest — every Ed setting
  writeup.md         the challenge slide's task text
  handout.md         OPTIONAL: a separate document slide
  images/            referenced by relative path from the markdown
  scaffold/          exactly what students start with
  solution/          reference solution
  testbase/          ExamRunner.java + Reflect.java + ONE JUnit 5 grader
  check/             OPTIONAL: checkstyle jar + config for the Check button
```

A lab on Ed is usually **two slides in one lesson**: handout (document
slide) on top, challenge (code slide) below. `push-doc` handles the
first, `push-challenge` the second.

## Commands

```bash
cd <repo>/ed-push

python3 ed_push.py doctor [--prod]
python3 ed_push.py push-challenge ../path/to/ed [--prod] [--dev]
#   ...and the same with --no-dry-run — THE USER RUNS THAT ONE, not you
python3 ed_push.py verify-challenge ../path/to/ed
python3 ed_push.py push-doc ../path/to/handout.md --slide N [--prod] [--no-dry-run]
python3 ed_push.py convert file.md          # offline preview of the Ed XML
```

- `--prod` targets `prod_course` from `config.yaml` instead of the dev
  course, and cross-checks that the lesson really belongs to it.
- `--dev` overrides the **lesson-title guardrail** only. Titles must
  match `Lab|Homework|HW` and must not match `Midterm|Exam|Final|Quiz`.
  A lesson called **"Challenges"** matches neither, so every bonus
  challenge push needs `--dev`. Adding `"Challenge"` to
  `allowed_lesson_patterns` in `config.yaml` removes that need.
- First push of a new challenge **clones a template slide**; there is no
  create-slide API. `template_slide` in `config.yaml` may be null, in
  which case a blank Code slide must be made in the Ed UI first.

**Getting ids from a slide URL** — never invent one:

```
https://edstem.org/us/courses/100745/lessons/175995/edit/slides/1030269
                              ^course        ^lesson              ^slide
```

Ask the user for that URL rather than guessing, and diff the `slide:`
line before handing over a push command — a one-digit slip overwrites
an unrelated slide.

## Porting a whole repo

Work one lab at a time, in this order. Full detail in
`references/porting-playbook.md`.

1. **Inventory** — what exists: starters, solutions, old autograder,
   handout (repo markdown vs. a Drive/Word doc TAs own).
2. **Build `ed/`** — scaffold, solution, testbase, writeup, manifest.
3. **Write or port the grader** — see `references/grader-design.md`.
   Most old Gradescope suites need rewriting, not porting.
4. **Reconcile points** to a round total.
5. **Verify locally** — compile grader and solution; run both.
6. **Ask for the slide URL** if there's no `slide:` yet, and read the
   lesson and slide ids out of it.
7. **Dry-run**, then hand the user the `--no-dry-run` command to run.
8. Tell them to read the ✓/✗ verify table, then open the slide and
   press Test once with the reference solution.

## Non-negotiable grader rules

These cause silent wrong scoring, not loud failures:

- **FLAT test classes.** Ed renders `@Nested` wrong — at most one
  failure per nested class. Group with `@DisplayName` prefixes.
- **`@Tag("score:N")` on every test**, integers, summing to `points:`.
  Untagged tests score 1 point each regardless of the total.
- **Every test independent.** Fresh instance per test, no shared
  mutable state, no ordering assumptions.
- **A test for method A must not fail because the student's method B is
  broken.** Isolate the dependency where the harness allows it.
- **Every test must fail on the untouched scaffold.** A test the
  skeleton already passes is free points; audit for these.
- **A single-element read can't verify multi-element behavior.** For
  linked lists, queues, stacks, BSTs — anything built by repeated
  insertion — testing with only `peek()`/`getFirst()` after adding
  several elements can miss a completely broken middle/back branch.
  Drain or walk the whole structure. See `references/mutation-testing.md`.
- **Nothing interactive or graphical.** Ed marks headless: Swing
  windows can't open and `JOptionPane` throws `HeadlessException`.

## Sharp edges that cost the most time

Full list in `references/api-gotchas.md`. The ones that bite hardest:

- The lesson UI renders `slide.content`, **not** `challenge.content` —
  write both or the description silently doesn't show.
- Filespace uploads **add/overwrite by filename, never delete**. A
  stray file must be removed in the Ed UI.
- Uploading a filespace without the binding PATCH changes nothing.
- A runnable ` ```java ` snippet compiles as **`Main.java`** whatever
  the class is called — name it `Main` or mark the fence ` norun `.
- Ed's document schema has **no horizontal rule**; `---` becomes an
  empty spacer.

## References

- `references/porting-playbook.md` — step-by-step for a lab or a repo.
- `references/challenge-yaml.md` — full manifest schema, worked examples.
- `references/grader-design.md` — test suites, scoring, independence,
  isolating student-vs-reference code, the ExamRunner/Reflect harness.
- `references/markdown-and-handouts.md` — Ed's markdown subset, runnable
  snippets, images, document slides.
- `references/api-gotchas.md` — the undocumented REST behaviour.
- `references/writeup-format.md` — house format for writeups, handouts,
  marks tables, feature tables and scaffold comments.
- `references/lab-catalog.md` — **memory**: every lab's lesson, slide,
  points, grader and migration state; which labs aren't migrated; which
  bonus challenges have no slide yet.
- `references/mutation-testing.md` — proving each grader test actually
  discriminates, not just that solution=100%/scaffold=0%; a worked
  example of a gap that survived both checks.
- `references/verify-before-reporting.md` — why "reported successful"
  and "verified successful" are different claims, with a real case
  where the difference caught two defects a subagent's summary missed.

## The ed-porter subagent

For anything beyond a one-line fix, delegate to the **`ed-porter`**
agent — it loads this skill, uses `Explore` for discovery so lab trees
never fill the main context, and verifies before reporting.

```
Agent(subagent_type="ed-porter",
      prompt="Port lab10 to Ed. It has no ed/ directory yet.")
```

## Provenance

Distilled from `ed-push/README.md`, `ed-push/TROUBLESHOOTING.md`, the
15 per-lab `ed/README.md` migration notes, and the tool source. Where
this file states a behaviour as fact, it was observed against the live
API or verified locally — not inferred. `references/mutation-testing.md`
and `references/verify-before-reporting.md` were added after the
livecodingexam port (2026-08-13), where independent re-verification —
not trusting a subagent's or a script's own "done" claim — caught
defects a first pass missed.
