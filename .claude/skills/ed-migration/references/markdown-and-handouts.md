# Markdown, writeups and handouts

Two markdown surfaces: `writeup.md` (the challenge slide's task text)
and a handout pushed as its own **document slide**.

## The supported subset

`writeup.md` and `push-doc` files support:

- `#`–`###` headings. **Deeper levels become bold paragraphs** — Ed has
  no h4. Structure accordingly rather than nesting five deep.
- Paragraphs, bullet and numbered lists, tables, links.
- `code`, **bold**, *italics* (both `*` and `_`).
- Images — local files auto-upload, `http(s)` URLs pass through.
- Fenced code blocks (below).

**No horizontal rule.** Ed's document schema has none; `---` becomes an
empty spacer paragraph. Harmless, but don't rely on it to divide
sections — use a heading.

Preview the conversion offline any time:

```bash
python3 ed_push.py convert path/to/file.md
```

## Code fences

- ` ```java ` → an Ed snippet with line numbers, **auto-detected as
  runnable** when it contains a main method.
- Force with ` ```java runnable ` or ` ```java norun `.
- A bare ` ``` ` fence stays a plain block — correct for terminal
  transcripts and for anything that shouldn't offer a Run button.

**The `Main.java` trap.** A runnable Java snippet is compiled as
`Main.java` no matter what the public class is called. A snippet like

````
```java
public class EmptyEventNameException extends Exception { ... }
```
````

that gets auto-marked runnable will fail on Run with *"class X is public,
should be declared in a file named X.java"*. Either name the class
`Main`, or mark the fence ` norun `. This bites most often on handouts
that demo a named class.

**Fences must be on their own line.** Writing ` ```public class Main { `
puts code on the fence line, and the block does not render as code. A
language tag is the only thing that belongs there:

````
```java
public class Main {
```
````

## Handouts as document slides

A lab is typically two slides in one lesson: handout on top, challenge
below.

```
my-lab/
  handout.md
  images/
    image1.png        referenced as ![alt](images/image1.png)
  challenge.yaml, writeup.md, scaffold/ ...
```

**First push** clones the blank document template into the lesson and
prints the new slide id:

```bash
python3 ed_push.py push-doc my-lab/handout.md --lesson 123456 --no-dry-run
```

Record that id — a comment in `challenge.yaml` is a good home. **Every
later push** targets it directly and never touches the challenge or its
grading config:

```bash
python3 ed_push.py push-doc my-lab/handout.md --slide 456789 --no-dry-run
```

Details:

- The slide title comes from the handout's first `# heading`; override
  with `--title`.
- Local images re-upload on every push. Old file ids are orphaned,
  which is harmless.
- Push the handout **before** the challenge on a fresh lesson so slides
  land in reading order. Order can also be fixed by dragging in the Ed
  lesson editor.
- The same lesson-title guardrails apply as for challenges.

## Coming from Google Docs or Word

Export to Markdown — Docs has File → Download → Markdown, and
`pandoc -t gfm` handles `.docx`. Put images beside the file, fix up
anything outside the supported subset, and push. **From then on the
Markdown is the source of truth.**

Note in the repo README when a handout is provisional because TAs own a
Drive/Word version — otherwise the next person edits the wrong copy.

## Writing the writeup

Conventions that have held up across the labs:

- Open with what the student is building, in one or two sentences.
- A **Marks** table, with the point split visible. If parts are graded
  independently, say so — a student who finishes one part should know
  they keep those marks.
- State plainly that **nothing is awarded for the untouched skeleton.**
- Say what the autograder can and cannot see. For anything graphical
  or interactive: Ed checks structure and state changes, a TA confirms
  real behaviour in lab.
- If style checking is on, say it's advisory and never affects points.
- Worked examples with exact expected output. **Verify every example
  against the reference solution** before pushing — stale examples in a
  handout are worse than none.
- End with the exact output format, and note that the grader matches it
  literally.

## Keeping split content consistent

When a challenge is split or a part moves elsewhere, these all drift:

- `writeup.md` — marks table, part list, submission text
- `handout.md` — task section, any per-part specs, images
- `challenge.yaml` — `points`, `build_command`, `run_command`,
  `check_command`, header comment
- `README.md` — the migration notes
- the grader — tests and the class javadoc's point breakdown

Grep for the moved part's name across the whole `ed/` directory
afterwards; a stale cross-reference is the usual leftover. Prefer
**minimal edits** to the markdown over regenerating a file wholesale —
a rewrite silently changes wording that had nothing to do with the task
and makes the diff impossible to review.
