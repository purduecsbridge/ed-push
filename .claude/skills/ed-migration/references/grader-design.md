# Writing Ed graders

Ed's `marking: unit` runs **one** JUnit 5 class from `testbase/`,
compiled alongside the submission and the other `testbase/` files.

## Scoring

- Tag every test `@Tag("score:N")` with an **integer**. Untagged tests
  score 1 point each regardless of `points:`.
- The tags must **sum exactly to `points:`** in `challenge.yaml`. Check
  it mechanically every time:

```bash
p=$(grep -E '^points:' ed/challenge.yaml | awk '{print $2}')
t=$(grep -ho 'score:[0-9]*' ed/testbase/*Test.java | cut -d: -f2 | awk '{s+=$1} END {print s}')
echo "yaml=$p tags=$t"
```

- Prefer a total that divides evenly across the work. If a lab has
  several independent parts, make each part stand on its own out of a
  round number, so a student who finishes one part is scored fairly.

## FLAT classes, always

Ed renders `@Nested` incorrectly — at most one failure shows per nested
class, so students lose the feedback for everything after the first
failure. Keep one flat class and carry grouping in the display name:

```java
@DisplayName("TicTacToe: Clicking a square marks it") @Tag("score:20")
```

## Every test must fail on the untouched scaffold

A test the skeleton already passes hands out free points. This is easy
to introduce accidentally when the scaffold *gives* students a line —
e.g. a scaffold containing `setLayout(new GridLayout(3, 3))` makes any
"uses a 3x3 GridLayout" test worthless.

Audit by running the grader against the scaffold and confirming it
scores zero. State the property in the class javadoc so the next
maintainer preserves it, and re-check whenever the scaffold changes.

Corollary: **audit for untested work too.** If the largest TODO in the
scaffold has no test, a student can stub it and still score full marks.

## Test independence

Each test must pass or fail on its own.

- **Construct a fresh instance inside every test.** Never share an
  instance across tests via a field.
- **No ordering assumptions.** JUnit does not guarantee method order.
- **Fresh state per sub-case.** If one test exercises several inputs
  that could cancel out — e.g. UP then DOWN on a paddle — build a new
  instance per input, or the net change is zero and a correct
  submission looks broken.
- `ExamRunner` already runs stdin-style submissions in a **fresh JVM
  per test** with its own working directory, so static state cannot
  leak between tests of that kind.

## Isolating the student's method A from their method B

If a test for `addEvent` fails only because the student's `getDate` is
broken, they are penalised twice for one mistake and the feedback
points at the wrong place.

**What the harness can actually do:**

- **Class granularity — supported.** `ExamRunner(main, companions...)`
  compiles the submission together with companion files. Pass the
  **reference** version of a collaborating class and the student's code
  is exercised against known-good dependencies:

  ```java
  new ExamRunner("EventCatalog.java",           // the student's
                 "DuplicateEventException.java", // reference companions
                 "InvalidDateException.java")
  ```

  Use this whenever the dependency lives in a different file.

- **Method granularity within one class — not possible** without
  bytecode rewriting. Java gives no way to swap one method of a
  student's class for the reference version.

**So for same-class dependencies, do this instead:**

1. **Order by dependency, and test leaves first.** Give the primitive
   method its own tests, so a failure there is reported once, at its
   real source.
2. **Set up state directly rather than through the helper.** Where a
   test needs a populated object, build that state by the most direct
   route available (constructor, direct field/array manipulation via
   reflection, or a sequence of already-tested calls) rather than by
   calling the untested helper.
3. **Choose inputs that don't exercise the helper's hard cases.** Test
   `addEvent` with a date the simplest possible `getDate` handles.
4. **Name the dependency in the failure message** when it is genuinely
   unavoidable:

   > `addEvent` put the event in the wrong position. Note this test also
   > relies on `getDate` — if that test is failing too, fix it first.

## Headless

Ed marks with no display.

- Swing windows cannot open. Game logic can only be checked
  **structurally** (right component types, listener wiring) and
  **behaviourally by proxy** (does the handler change any state).
- `JOptionPane` throws `HeadlessException`. If a correct submission
  shows a dialog on some path, the test must tolerate it — either catch
  it deliberately, or drive the action on a daemon thread and stop
  waiting:

  ```java
  Thread t = new Thread(() -> {
      try { button.doClick(); } catch (Throwable ignored) { }
  });
  t.setDaemon(true);
  t.start();
  t.join(3000);
  ```

  State changes happen *before* the dialog opens, so the object is in
  the right state either way.
- Set `System.setProperty("java.awt.headless", "true")` in a static
  initializer so behaviour is the same locally and on Ed.
- Say so in the writeup: TAs still confirm real gameplay in lab.

## Name-agnostic behavioural checks

Scaffolds usually don't fix variable names, so a grader cannot assert on
a field called `speedX`. The portable technique: snapshot **every**
declared numeric/boolean field, fire the handler, snapshot again, and
assert something changed.

That catches an empty tick handler without dictating the student's
design. It is weak — it cannot tell *correct* from *different* — so pair
it with structural checks and a TA's eyes.

## The harness

Both files live in `testbase/`, and **each lab vendors its own copy** so
a pushed challenge is self-contained.

- **`ExamRunner.java`** — compiles a submission and runs it in a fresh
  JVM per test with stdin piped at process level. This is what makes
  classic (`class` + `static main` + `Scanner`) and modern (implicit
  class + `IO`) submissions grade identically. Also stages input files
  into the run directory.
- **`Reflect.java`** — grades class/method-style submissions through a
  URLClassLoader over ExamRunner's compile output, independent of the
  grader's own classpath, tolerant of member visibility and either
  dialect. Key methods: `load`, `construct`, `call`,
  `callExpectingThrow`, `hasConstructor`.

`Reflect` is **shared across labs 09+**. Do not loosen its general
methods to fix one lab — add a narrow new method instead, or you change
every other lab's grader silently.

## Failure messages

The message is the student's entire debugging experience. Include what
was expected, what happened, and where to look. Prefer

> `EmptyEventNameException` needs either a `(String message)`
> constructor or a no-arg constructor.

over

> assertion failed

For input-driven tests, echo the input back (truncated if large).

## Local verification before every push

```bash
CP=$(find ~/.m2/repository/org/junit ~/.m2/repository/org/opentest4j \
        ~/.m2/repository/org/apiguardian -name '*.jar' | tr '\n' ':')
(cd ed/testbase && javac -cp "$CP." -d /tmp/out *.java)   # grader compiles
(cd ed/solution && javac *.java)                          # solution compiles
```

Then confirm, by whatever driver is quickest: reference solution passes
everything, untouched scaffold fails everything, and a deliberately
broken solution fails exactly the tests meant to catch it.

For algorithmic challenges, fuzz the reference solution against an
**independently written** implementation — ideally one using a different
method — rather than trusting it because it looks right.
