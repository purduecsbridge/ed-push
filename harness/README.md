# Grader harness

Canonical copies of the two harness files that lab graders build on.
Copy both into a lab's `testbase/` — each lab vendors its own copy so
a pushed challenge is fully self-contained on Ed.

- **`ExamRunner.java`** — compiles a submission (optionally together
  with companion files: `new ExamRunner(main, companions...)`) and
  runs it in a fresh JVM per test, stdin piped at process level,
  with helpers for transcript assertions and run-directory files.
  The fresh JVM is what makes classic (`class` + `static main` +
  `Scanner`) and modern (implicit class + `IO`) submissions grade
  identically, with no static state carried between tests.
- **`Reflect.java`** — reflective grading for class/method-style
  submissions: loads classes from an ExamRunner's compile output via
  a URLClassLoader (independent of the grader's own classpath), with
  `construct` / `call` / `callExpectingThrow`, inherited-method
  lookup, tolerance for any member visibility and either dialect,
  and novice-readable failure messages.
