# ed-push

Push complete Ed lessons — handout slides and autograded code
challenges — from plain directories in version control. Built for
Purdue CS Bridge so TAs can edit a lab locally and re-publish it to
[Ed](https://edstem.org) with one command, with every field verified
after the push.

**What it manages:** challenge description + slide content, build/run
commands (including the editor-UI fields), unit-marking config
(JUnit 5 testcase, per-test points, time limits), the four challenge
filespaces (scaffold / solution / testbase / check), workspace &
feedback toggles, the advisory style checker, handout document slides
with images, and Markdown → Ed-XML conversion for all of it.

> This is a third-party client of Ed's undocumented REST API,
> reverse-engineered from the web editor. It is not affiliated with
> or endorsed by Ed. API behavior may change without notice — the
> post-push verification exists precisely so silent changes get
> caught.

## Quickstart

1. **Token.** Create an API token on Ed (Settings → API tokens) and
   either `export ED_API_TOKEN=...` or write it to
   `~/.config/ed/token`. The token acts as **you** — use your own,
   never a shared one, and never commit it.
2. **Install.** `pip install -r requirements.txt` (PyYAML +
   websocket-client). Python 3.10+.
3. **Configure.** `cp config.yaml.example config.yaml` and fill in
   your course id and two blank template slides (one code slide, one
   document slide — create them once in a scratch lesson via the Ed
   UI and copy their ids from the editor URL). `config.yaml` is
   gitignored.
4. **Check.** `python3 ed_push.py doctor` — verifies the token, the
   course, and dependencies.
5. **Push.** Point at a challenge directory (see
   `example-challenge/`):

   ```bash
   python3 ed_push.py push-challenge example-challenge/               # dry-run (default)
   python3 ed_push.py push-challenge example-challenge/ --no-dry-run  # actually push
   ```

   Every real push ends with a ✓/✗ verification table that GETs the
   challenge back and asserts every manifest-driven field. All ✓ or
   the command exits nonzero — don't use a challenge that failed
   verification.

## A challenge directory

```
my-lab/
  challenge.yaml     the manifest (all Ed settings; schema below)
  writeup.md         the challenge slide's description (Markdown)
  scaffold/          exactly the files students start with
  solution/          the reference solution
  testbase/          the grader: a JUnit 5 test class (+ harness files)
  check/             OPTIONAL: files for Ed's "Check" button
                     (e.g. a checkstyle jar + config)
```

The directory in git is the **source of truth**: edit files → dry-run
shows what would change → `--no-dry-run` pushes → the verify table
confirms it landed. After the first push, record the printed slide id
as `slide:` in the manifest so re-pushes update the same slide
instead of cloning a new one.

## Commands

| Command | What it does |
|---|---|
| `doctor` | Token, course reachability, dependency check |
| `convert FILE.md` | Print a Markdown file as Ed XML (offline preview) |
| `push-challenge DIR [--no-dry-run] [--force]` | Push manifest + writeup + all filespaces; auto-verify |
| `verify-challenge DIR` | Re-run the field verification any time (exit 0/1; handy in CI) |
| `push-doc FILE.md --lesson N \| --slide N [--title T] [--hidden] [--no-dry-run] [--force]` | Push Markdown as a **document slide** (handouts). First push clones the doc template into `--lesson` and prints the new slide id; re-push with `--slide N`. Local images referenced as `![alt](path.png)` are uploaded automatically. |

Dry-run is the default everywhere; `--no-dry-run` is always the flag
that makes it real.

## challenge.yaml schema

| Key | Required | Ed knob it drives |
|---|---|---|
| `title` | ✓ | Slide title |
| `lesson` | ✓ | Target lesson id (globally unique — no course id needed) |
| `slide` | after 1st push | Existing code slide to update (else the template is cloned) |
| `build_command` / `run_command` | ✓ | Build/Run — written to `settings.*`, the run ticket (what the editor UI shows), and the marking build |
| `marking` | – | `unit` (default) or `none` (dropbox-style, no autograding) |
| `points` | unit | Total automatic points |
| `testcase_file` | unit | The JUnit 5 class in `testbase/` that Ed runs |
| `time_limit_seconds` | – | Marking wall/CPU limit (default 60) |
| `per_testcase_scores` | – | Per-test score display (default true) |
| `workspace` | – | The "Workspace" checkbox (full IDE + debugger for students) |
| `feedback` | – | Students see test output (default true) |
| `git_submission` | – | Per-challenge git submission toggle (default false) |
| `check_command` | – | Enables Ed's **Check** button; runs with `check/` files present (advisory style checking) |
| `attempts` | – | Attempts allowed per interval |
| `template_slide` | – | Per-challenge template override |
| `hidden` | – | Create the slide hidden (default: visible) |

## Writing graders

Ed's unit marking runs **one** JUnit 5 testcase file, compiled next
to the submission and the other `testbase/` files.

- **Per-test points:** tag every test `@Tag("score:N")` — integers;
  without tags Ed scores 1 point per test. Make the tags sum to
  `points:`.
- **Keep test classes FLAT.** Ed renders `@Nested` classes
  incorrectly (at most one failure shown per nested class). Carry
  grouping in `@DisplayName` prefixes instead.
- **The harness** (`harness/`): `ExamRunner.java` compiles a
  submission and runs it in a **fresh JVM** per test with stdin piped
  at process level — which is what makes classic
  (`class` + `static main` + `Scanner`) and modern
  (implicit class + `IO`) submissions grade identically, with no
  static-state leakage. `Reflect.java` grades class/method-style
  submissions via a URLClassLoader over ExamRunner's compile output —
  independent of the grader's classpath, tolerant of member
  visibility and either dialect. Copy both into a lab's `testbase/`
  (each lab vendors its own copy so pushed labs are self-contained).
- Give assertions **novice-readable messages** that include the
  actual output — the message is the student's whole debugging
  experience.
- Verify locally before pushing: reference solution passes, the
  untouched scaffold fails the right tests with readable messages,
  and a deliberately-wrong solution fails exactly the tests that
  should catch it.

## Markdown conversion notes

`writeup.md` and `push-doc` files support: `#`–`###` headings (deeper
levels become bold paragraphs — Ed has no h4), paragraphs, bullet and
numbered lists, tables, links, `code`, **bold**, *italics* (both `*`
and `_`), images (local files auto-upload), and fenced code blocks:
` ```java ` becomes an Ed snippet with line numbers — **runnable is
auto-detected** when the snippet contains a main method (force with
` ```java runnable ` / ` ```java norun `); bare ` ``` ` fences stay
plain blocks (right for terminal transcripts). Known limitation: Ed's
document schema has no horizontal rule — `---` becomes an empty
spacer paragraph.

## Guardrails

`push-challenge` and `push-doc` refuse to touch a lesson whose title
matches a blocked pattern (default: Midterm/Exam/Final/Quiz) or fails
to match an allowed one (default: Lab/Homework/HW) — this tool is for
labs and homework; exam content stays point-and-click unless you pass
`--force` deliberately. Patterns live in `config.yaml`.

Two more safety properties worth knowing: workspace uploads **add or
overwrite by filename, never delete** (remove a stray file in the Ed
UI), and nothing is ever pushed without `--no-dry-run`.

## See also

- `TROUBLESHOOTING.md` — the API's sharp edges, in the order you'll
  hit them.
- `example-challenge/` — a minimal working challenge directory.

## License

MIT — see `LICENSE`.
