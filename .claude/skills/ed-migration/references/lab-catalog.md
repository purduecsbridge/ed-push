# Lab catalog — the migration state of the repo

Ground truth as of the last survey. **Re-derive rather than trust** if
something looks stale: every number here comes from
`<lab>/ed/challenge.yaml` and the graders, and can be regenerated with
the script at the bottom.

## Migrated labs

Every lab is **100 points**. Lesson ids are sequential:
`lesson = 175755 + N`.

| lab | title | lesson | slide | testcase | tests |
|---|---|---|---|---|---|
| lab01 | Hello + Copycat | 175756 | 1020022 | `Lab01Test.java` | 4 |
| lab02 | Debugging | 175757 | 1020023 | `Lab02Test.java` | 4 |
| lab03 | Primitives and Strings | 175758 | 1020025 | `Lab03Test.java` | 9 |
| lab04 | Strings Challenge | 175759 | 1020027 | `Lab04Test.java` | 7 |
| lab05 | Intro to Selection | 175760 | 1020029 | `Lab05Test.java` | 13 |
| lab06 | Selection Challenge | 175761 | 1020031 | `Lab06Test.java` | 21 |
| lab07 | Intro to Repetition | 175762 | 1020033 | `Lab07Test.java` | 11 |
| lab08 | Repetition Challenge | 175763 | 1020035 | `Lab08Test.java` | 11 |
| lab09 | Intro to Arrays | 175764 | 1020037 | `Lab09Test.java` | 16 |
| lab11 | Classes | 175766 | 1020041 | `Lab11Test.java` | 45 |
| lab13 | Inheritance | 175768 | 1020045 | `Lab13Test.java` | 49 |
| lab14 | Exceptions | 175769 | 1020047 | `Lab14Test.java` | 25 |
| lab15 | GUI Games | 175770 | 1020049 | `Lab15Test.java` | 5 |
| lab16 | ArrayLists | 175771 | 1020050 | `Lab16Test.java` | 36 |
| lab17 | Dynamic Data Structures | 175772 | 1020053 | `Lab17Test.java` | 23 |

**Not migrated:** `lab10`, `lab12` (no `ed/`), and `lab-template`.
`lab15-new` / `lab16-new` exist at the repo root — **the `-new` repos
are the live source; the plain ones are obsolete.** Check before
working.

## Bonus challenges

All on lesson **175995**, titled "Challenges" — which matches no
allowed lesson-title pattern, so **every push here needs `--dev`**.

| challenge | slide | points | testcase | tests |
|---|---|---|---|---|
| day1/digit-fun | 1021877 | 100 | `DigitFunTest.java` | 3 |
| day1/string-fun | — (`lesson: 0`) | 100 | `StringFunTest.java` | 4 |
| day2/word-fun | 1022033 | 100 | `WordFunTest.java` | 3 |
| day2/word-extra-fun | 1022040 | 100 | `WordExtraFunTest.java` | 5 |
| day3/selection-fun | 1022342 | 100 | `SelectionFunTest.java` | 18 |
| day3/selection-extra-fun | 1025262 | 100 | `SelectionExtraFunTest.java` | 20 |
| day4/loops-fun | 1025458 | 100 | `LoopsFunTest.java` | 20 |
| day5/ridge | 1025495 | 100 | `RidgeTest.java` | 20 |
| day6/crux | — not created | 100 | `CruxTest.java` | 20 |
| day6/silhouette | — not created | 100 | `SilhouetteTest.java` | 20 |
| day7/gui-games | 1030269 | 300 | `GamesTest.java` | 10 |

**`day1/string-fun` has `lesson: 0` and no slide** — a placeholder that
was never finished. Do not push it without fixing the lesson id.

**`day6/crux` and `day6/silhouette` have no slide yet.** Create a blank
Code slide in lesson 175995 and paste the id in first.

**`challenge-bonus/` is not inside any git repository.** Individual labs
(`lab14/`, `lab15/`) are their own repos; the parent directory is not.
Anything under `challenge-bonus/` is therefore **untracked** — check
`git rev-parse --show-toplevel` before assuming a move preserves history.

## Shape conventions by lab type

**Intro labs (01–09)** — stdin/stdout programs. Graded through
`ExamRunner`, which runs each test in a fresh JVM with stdin piped, so
classic `static main` + `Scanner` and modern implicit-class + `IO`
submissions grade identically. Test counts are low (4–16); points are
larger per test.

**Class/method labs (09+)** — graded through `Reflect` over
`ExamRunner`'s compile output. Test counts climb sharply (lab11 has 45,
lab13 has 49) because each method gets declaration + behaviour tests at
2–5 points each. `Reflect` is **shared across these labs** — never
loosen its general methods to fix one lab; add a narrow new method.

**Bonus challenges** — self-contained algorithmic problems, almost
always **exactly 20 tests × 5 points**, 18 small hand-built cases plus 2
large generated ones. Large cases are built by a deterministic LCG
mirrored in Python and Java so the expected values can be computed
offline and the Java test file stays small:

```java
seed = seed * 6364136223846793005L + 1442695040888963407L;
long v = (seed >>> 33) % (max + 1L);
```

**GUI labs (15, day7)** — headless marking means structural checks plus
name-agnostic behavioural ones only. A TA confirms real gameplay.

## The recurring per-lab decisions

Across the 15 `ed/README.md` files, in frequency order:

1. **Handout** — 10 labs note it. Usually authored fresh, because the
   repo's version was a stub and TAs own a Drive/Word original. Mark it
   provisional when that's true.
2. **Suite rewrite** — 8 labs. The old Gradescope suite was rewritten,
   not ported. Assume rewrite is the default.
3. **Starters** — 7 labs. Frequently none existed and a scaffold had to
   be authored from the solution by gutting bodies into TODOs.
4. **Lab-local checkstyle** — where a repo's own files break the shared
   style (e.g. lowercase class names `pingpong`, `flappybird`), the lab
   ships a relaxed `cs-style.xml`. Note the deviation in a comment.

## Regenerating this table

```bash
printf "%-34s %-8s %-9s %-7s %-24s %s\n" LAB LESSON SLIDE POINTS TESTCASE TESTS
for y in $(ls -d lab*/ed challenge-bonus/*/*/ed 2>/dev/null | sort); do
  c=$y/challenge.yaml; [ -f "$c" ] || continue
  printf "%-34s %-8s %-9s %-7s %-24s %s\n" "$(dirname $y)" \
    "$(grep -E '^lesson:' $c | awk '{print $2}')" \
    "$(grep -E '^slide:' $c | awk '{print $2}')" \
    "$(grep -E '^points:' $c | awk '{print $2}')" \
    "$(grep -E '^testcase_file:' $c | tr -d '"' | awk '{print $2}')" \
    "$(grep -hc '@Test' $y/testbase/*Test.java 2>/dev/null | paste -sd+ - | bc)"
done
```

Points/tag reconciliation across everything at once:

```bash
for y in $(ls -d lab*/ed challenge-bonus/*/*/ed 2>/dev/null); do
  p=$(grep -E '^points:' $y/challenge.yaml | awk '{print $2}')
  t=$(grep -ho 'score:[0-9]*' $y/testbase/*Test.java 2>/dev/null | cut -d: -f2 | awk '{s+=$1} END {print s+0}')
  [ "$p" = "$t" ] || echo "MISMATCH $y yaml=$p tags=$t"
done
```
