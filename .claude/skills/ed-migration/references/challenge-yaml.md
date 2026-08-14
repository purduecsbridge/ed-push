# challenge.yaml

The manifest. Every Ed setting for a challenge slide lives here; the
push tool drives the API from it.

## Schema

| Key | Required | What it drives |
|---|---|---|
| `title` | ✓ | Slide title |
| `lesson` | ✓ | Target lesson id (globally unique — no course id needed) |
| `slide` | after 1st push | Existing code slide to update; without it the template is cloned |
| `build_command` | ✓ | Build — written to `settings.*`, the run ticket (what the editor UI shows), and the marking build |
| `run_command` | ✓ | Run — same three places |
| `marking` | – | `unit` (default) or `none` (dropbox-style, no autograding) |
| `points` | unit | Total automatic points |
| `testcase_file` | unit | The JUnit 5 class in `testbase/` Ed runs |
| `time_limit_seconds` | – | Marking wall/CPU limit (default 60) |
| `per_testcase_scores` | – | Per-test score display (default true) |
| `workspace` | – | The "Workspace" checkbox — full IDE + debugger |
| `feedback` | – | Students see test output (default true) |
| `git_submission` | – | Per-challenge git submission toggle (default false) |
| `check_command` | – | Enables the **Check** button; runs with `check/` files present |
| `attempts` | – | Attempts allowed per interval |
| `template_slide` | – | Per-challenge template override |
| `hidden` | – | Create the slide hidden (default visible) |

## Minimal single-file challenge

```yaml
title: "Bonus Challenge Lab: Tarns"
lesson: 175995
points: 100
build_command: "javac Tarns.java"
run_command: "java Tarns"
testcase_file: "TarnsTest.java"
time_limit_seconds: 120
per_testcase_scores: true
workspace: true
feedback: true
slide: 1025495
```

## Multi-file challenge

Two or three independent programs in one challenge works, and is the
right shape when the parts are related but separately gradable. Each
filespace simply holds more files; the grader builds one `ExamRunner`
per program so they compile and run independently.

```yaml
title: "Bonus Challenge: Snake, Pong and Flappy Bird"
lesson: 175995
points: 300
build_command: "javac Snake.java pingpong.java flappybird.java"
run_command: |
  FILES=(*.java)
  if [ ${#FILES[@]} -eq 1 ]; then
    java "${FILES[0]%.java}"
  else
    PS3="Which file do you want to run? Enter a number: "
    select f in "${FILES[@]}"; do
      if [ -n "$f" ]; then
        java "${f%.java}"
        break
      fi
      echo "Not a valid choice, try again."
    done
  fi
testcase_file: "GamesTest.java"
per_testcase_scores: true
workspace: true
feedback: true
check_command: "java -jar checkstyle-13.8.0-all.jar -c cs-style.xml Snake.java pingpong.java flappybird.java"
slide: 1030269
```

That `run_command` is the standard multi-file pattern: one file runs
straight, several offer a picker.

State in the writeup that the parts are graded independently, so a
student who finishes one knows they keep those marks.

## The slide id

- **Globally unique**, and it is what routes the push. A wrong id
  overwrites an unrelated slide, silently.
- Read it from the Ed URL:
  `…/lessons/<lesson>/edit/slides/<slide>`.
- There is no create-slide endpoint. First push clones a template and
  prints the new id — record it immediately.
- If `template_slide` in `config.yaml` is null, create a blank **Code**
  slide in the Ed UI yourself and paste its id in before pushing.
- Leave a placeholder comment for challenges not yet created:

  ```yaml
  # No slide id yet — create a blank CODE slide in lesson NNNN via the
  # Ed UI and paste its id here before pushing. ed-push refuses to guess.
  # slide: 0
  ```

**Treat the slide line as dangerous when editing.** Rewriting a manifest
wholesale is an easy way to typo a digit; diff that line specifically
before pushing.

## Points must reconcile

`points:` must equal the sum of `@Tag("score:N")` in the grader. Nothing
enforces it — a mismatch just caps students below the stated total.

## check/ and the Check button

`check_command` turns on Ed's Check button, run with the `check/`
filespace present. Used for **advisory** checkstyle; it never affects
points, and the writeup should say so.

A lab-local `cs-style.xml` variant is normal — e.g. tolerating lowercase
class names when the repo's own files are named that way. Note the
deviation in a comment so nobody "fixes" it back.

## Header comments

Manifests carry a comment block explaining the non-obvious choices —
why marking is structural, what moved where, why a style config is
lab-local. That block is the first thing the next TA reads. Keep it
current when the challenge changes.
