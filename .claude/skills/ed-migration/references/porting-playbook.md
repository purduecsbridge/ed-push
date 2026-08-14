# Porting playbook

One lab at a time. A whole repo is this loop repeated, not a batch job.

## 1. Inventory

Before writing anything, find out what actually exists:

```bash
find <lab> -type f -not -path "*/target/*" -not -path "*/.git/*" | sort
```

Answer:

- Are there **starter files**? Often none exist, or they're a solution
  with the bodies still in.
- Is there a **reference solution**, and does it compile today?
- Is there an **old autograder** (Gradescope)? Assume it needs
  rewriting, not porting — across the labs migrated so far, "suite
  rewrite" is the most common note by a wide margin.
- Where does the **handout** live — repo markdown, or a Drive/Word doc
  the TAs own? If the latter, the repo copy is provisional; say so in
  the README.
- Is there a **newer parallel repo** (`labNN-new`)? Check before
  working; the old one is often obsolete.

## 2. Build the `ed/` directory

```
<lab>/ed/
  challenge.yaml  writeup.md  handout.md  images/
  scaffold/  solution/  testbase/  check/
```

- **scaffold** is exactly what students start with. Thin. Signposts,
  not strategy — the handout carries the teaching. A scaffold that
  hands over a line makes any test of that line free points.
- **solution** must compile exactly as Ed will build it:
  `cd ed/solution && javac <the build_command's files>`.
- **testbase** vendors its own `ExamRunner.java` and `Reflect.java` so
  the pushed challenge is self-contained.

**Keep the solution and the scaffold in the same design.** If the
scaffold hands students `JButton[] board` and says "check the text of
each button", a solution that instead keeps a parallel `String[]` will
confuse everyone who compares the two.

## 3. Write the grader

See `grader-design.md` in full. The checklist:

- Flat class, `@Tag("score:N")` summing to `points:`.
- Every test independent; fresh instance per test.
- Every test fails on the untouched scaffold.
- No test is free; no major TODO is untested.
- Headless-safe.
- Novice-readable failure messages that echo the input.

## 4. Reconcile the points

```bash
p=$(grep -E '^points:' ed/challenge.yaml | awk '{print $2}')
t=$(grep -ho 'score:[0-9]*' ed/testbase/*Test.java | cut -d: -f2 | awk '{s+=$1} END {print s}')
[ "$p" = "$t" ] && echo "OK $p" || echo "MISMATCH yaml=$p tags=$t"
```

## 5. Verify locally

```bash
CP=$(find ~/.m2/repository/org/junit ~/.m2/repository/org/opentest4j \
        ~/.m2/repository/org/apiguardian -name '*.jar' | tr '\n' ':')
(cd ed/testbase && javac -cp "$CP." -d /tmp/g *.java)   # grader compiles
(cd ed/solution && javac *.java)                        # solution compiles
(cd ed/scaffold && javac *.java)                        # scaffold compiles too
```

The scaffold **must** compile — students start from it, and a scaffold
that doesn't build makes every test report a compile error instead of
useful feedback.

Then: reference solution passes all; scaffold passes none.

For algorithmic challenges, fuzz the reference against an
**independently written** implementation before trusting it. Writing
the reference twice by the same reasoning proves nothing; use a
different method (brute force vs. the clever one) and a few hundred
random inputs.

## 6. Dry-run, then hand over the push

**Do not run the real push.** Dry-run to validate, then give the user
the command. If there is no `slide:` yet, ask them for the slide URL
first and take the ids out of it.

```bash
cd <repo>/ed-push
python3 ed_push.py push-challenge ../<lab>/ed --prod              # you run this
python3 ed_push.py push-challenge ../<lab>/ed --prod --no-dry-run # they run this
```

Add `--dev` when the lesson title isn't `Lab|Homework|HW` — bonus
challenges on a lesson called "Challenges" always need it.

Handout, if there is one, **before** the challenge on a fresh lesson.

Read the ✓/✗ verify table. Any ✗ means the challenge is not usable.

## 7. Confirm in the UI

Open the slide, eyeball the description, paste the reference solution
and press Test once. The API can report success on a challenge that is
still wrong for a student.

## Splitting or moving a challenge

When part of a lab becomes its own challenge:

1. Move the files (`git mv` where both ends are in the same repo — check
   that, since `challenge-bonus/` may not be inside any repo).
2. Split the grader; give the new class its own name and point total.
3. New `challenge.yaml`, new slide id, new writeup.
4. Copy `ExamRunner.java`, `Reflect.java`, `check/`, and any **images
   the moved sections reference**.
5. Update the original's `points`, `build_command`, `run_command`,
   `check_command`, writeup, handout and README.
6. Grep the whole tree for the moved part's name and for the old path.
7. Re-verify **both** sides: graders compile, solutions compile, points
   reconcile.
8. Remember the Ed workspace still holds the old files — filespace
   uploads never delete. Remove them in the UI.

## Repo-level cautions

- Labs are often **individual git repos** (`lab14/`, `lab15/`), while
  the parent directory is not a repo at all. Check
  `git rev-parse --show-toplevel` before assuming a move is tracked —
  moving a directory out of a lab repo silently drops it out of version
  control entirely.
- Branches get rewritten during migration. A `git stash` taken on a
  pre-rewrite commit will conflict violently when popped; the markers
  say `Updated upstream` / `Stashed changes`, which is a stash pop, not
  a merge. Check `git log --oneline <branch>..origin/main` before
  assuming which side is newer — the branch you're on is not
  necessarily ahead.
- Before deleting a local branch whose remote is gone, confirm it's
  merged: `git log --oneline origin/main..<branch>` must be empty.

## Recurring migration notes worth writing down

Every `ed/README.md` should record, briefly:

- Which source repo the content came from, and which one is obsolete.
- What was rewritten vs. carried over.
- Anything deliberately lab-local (e.g. a relaxed checkstyle config).
- What the grader **cannot** check, and what a TA must confirm live.
- The point split, matching the grader.

Keep that block accurate. It is the first thing the next TA reads, and
a stale one — a point split that no longer matches the tests, say — is
worse than nothing.
