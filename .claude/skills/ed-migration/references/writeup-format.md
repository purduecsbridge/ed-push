# writeup.md and handout.md — house format

The shape every migrated lab converged on. Follow it so slides read
consistently and so the next TA can find things.

## writeup.md skeleton

```markdown
# Lab NN submission                     ← or "Bonus: <Name>"

<1–2 sentences: what the workspace contains and what to build.>

**Work and PLAY the game locally in IntelliJ** — <any constraint that
bites, e.g. Swing can't open in the Ed workspace.> Use Ed to submit:
paste your finished files here, press **Run** to confirm everything
compiles, and try **Check** for style advice (style is advisory).

## Marks

**<N> points — <how it splits>:**

| section | points |
|---|---|
| ... | ... |

<What isn't graded. What earns nothing. What the autograder can't see.>

---

## Reference: what you need

<Any API/formulas/constants, stated once.>

## Task

### <given worked example, if any>
### <the thing to build>

| Feature | What it needs to do |
|---------|----------------------|
| ... | ... |

## Submission

Paste your files into the **<slide name>** workspace and press **Run**
to confirm they compile. **Check** gives style advice; style never
affects points.
```

## Tables

Two table shapes do almost all the work.

**Marks table** — one row per independently-scored section, with the
split shown in parentheses so it's auditable against the grader:

```markdown
| section | points |
|---|---|
| Snake | 100 (34 + 33 + 33) |
| Pong | 100 (34 + 33 + 33) |
| Flappy Bird | 100 (4 checks x 25) |
```

Use `x` not `×` — it survives every export path.

**Feature table** — the workhorse for "what to build". Two columns:
the thing, and what it must do. Put the *hint* in the second column,
never a code answer:

```markdown
| Feature | What it needs to do |
|---------|----------------------|
| Win detection | After each move, check all 8 possible three-in-a-row lines (3 rows, 3 columns, 2 diagonals). Make sure this check happens after every single move! |
```

Rules that hold across the labs:

- **Header separator is `|---|---|`** — no alignment colons. They add
  nothing on Ed and churn diffs.
- **One row per idea.** Long prose in a cell is fine; a second idea in
  the same cell is not.
- **Never wrap a cell across lines.** Ed's converter treats the row as
  one line; a wrapped cell breaks the table silently.
- **Escape pipes inside cells** as `\|`.
- A trailing `(Stretch)` row is the convention for optional extras.

## Prose conventions

- **Second person, present tense.** "You start at the top-left cell."
- **Bold the trap**, once, where it bites: *"Water stands at the LOWER
  of its two lips, not the higher."*
- State the constraint positively and early — "One array is enough",
  "Loops, if statements and int variables only — no arrays."
- Give **exact expected output** in a fenced block, and say the grader
  matches it literally:

  > Match the labels and spacing exactly — the grader checks the value
  > printed after `Chord: `.

- **Verify every worked example against the reference solution** before
  pushing. Stale examples are worse than none — they teach the wrong
  answer and generate TA tickets.

## Scaffold comments

Thin. Numbered signposts, no strategy — the writeup teaches:

```java
public static void main(String[] args) {
    Scanner s = new Scanner(System.in);

    // 1. Read the ridge.

    // 2. Work out how deep the water is at each point.

    // 3. Count the pools.

    // Print exactly:
    // Tarns: <how many separate pools>
    // Largest: <volume of the biggest>
    // Deepest: <deepest point anywhere>
}
```

Target ~25–30 lines. Before deleting a hint, confirm the writeup
carries it; grep for the idea rather than assuming.

**A scaffold hint that is factually wrong is worse than a missing one.**
When limits change, re-read every comment — e.g. "one of these doesn't
fit in an `int`" survived a rescale that made everything fit, and would
have sent students chasing a `long` they didn't need.

## Editing an existing writeup

**Make minimal edits. Do not regenerate the file.** Rewriting wholesale
silently changes wording unrelated to the task and makes the diff
unreviewable. If a section must go, delete that section and leave the
rest byte-identical.

After any split or move, these drift together — check all of them:

- `writeup.md` marks table, part list, submission text
- `handout.md` task section and per-part specs
- `challenge.yaml` — `points`, `build_command`, `run_command`,
  `check_command`, header comment
- `ed/README.md` migration notes and point split
- the grader's class javadoc breakdown

Then grep the whole `ed/` tree for the moved part's name.
