# Ed's undocumented API — sharp edges

`ed_push.py` already handles all of this. This file exists so a
confusing symptom is recognisable and nobody re-derives the map.

## Requests

- **Base is `https://us.edstem.org/api`** — not `/v1`, and note the
  `us.` region prefix. Blog posts and docs online describe the
  Australian deployment; **ids and hosts do not cross regions.** Git
  remote is `git.us.edstem.org` likewise.
- **403 from Cloudflare on everything?** Python's default User-Agent is
  blocked. Send a browser UA. The sahara upload host needs it too.
- **Auth is `Authorization: Bearer <token>`**, from Settings → API
  tokens. The browser uses a different header (`x-token` with a session
  JWT) — devtools captures will show that; the Bearer token works on the
  same endpoints.

## Slides and challenges

- **Updating a challenge is `PATCH /challenges/{id}` with the FULL
  object.** GET fresh, mutate, PATCH the whole thing back. `PUT` 404s,
  and sparse objects can drop sibling fields.
- **Updating a slide is `PUT /lessons/slides/{id}` with a FORM-ENCODED
  body** `slide=<json-string>`. A plain JSON body gets
  400 "Missing slide".
- **The lesson UI renders `slide.content`, not `challenge.content`.**
  Write the description XML to **both** or it silently doesn't show.
- **No create-slide endpoint.** New slides come from cloning:
  `POST /lessons/slides/{template}/clone` with `{lesson_id, is_hidden}`.
  Keep one blank code slide and one blank document slide as permanent
  templates.
- **The editor UI reads build/run from the tickets**
  (`tickets.run_standard.*`), not `settings.*`. Set both or the fields
  look empty in the UI while the API insists they're set.
- **The "Workspace" checkbox is `features.full`**, not
  `features.connect` — connect can be true with the box unchecked.
  Feedback visibility is `features.feedback`.
- **Lesson creation ignores the title in the body.**
  `POST /courses/{id}/lessons` then PUT the title back; new lessons
  arrive hidden as "Untitled Lesson".
- **Slide ids don't come out in a predictable order** when pushing a
  handout and challenge back to back. Never infer an id from sequence —
  read `challenge_id` off the pushed slide.

## Filespaces (scaffold / solution / testbase / check)

- **No git or plain-REST door.** Uploads ride the workspace-ticket
  system: `POST /challenges/{id}/connect/{which}` → websocket to sahara
  (first frame carries the workspace id) → per-file upload tickets →
  multipart POST per file → **PATCH the returned hash onto the challenge
  as `{which}_hash` to BIND it.**
- **Uploading without the binding PATCH changes nothing.** This is the
  most confusing failure mode: the upload "succeeds" and the workspace
  is unchanged.
- **Uploads add or overwrite by filename — they never delete.** A file
  you removed from the repo stays in the Ed workspace until you delete
  it in the UI. Check this after renaming or splitting a challenge.
- `check` is a fourth filespace behind the Check button
  (`features.check` + `settings.check_command`), same protocol.

## Marking

- **`@Nested` JUnit classes render wrong** — at most one failure shown
  per nested class. Keep test classes flat.
- **Per-test points are `@Tag("score:N")`**, integers. Untagged tests
  score 1 point each regardless of the challenge total.
- A submission that fails to build shows an **"Errored"** banner with
  compiler output instead of test results. For a debugging lab that's a
  feature; don't mistake it for a grader crash.
- Ed provides JUnit 5 for `marking: unit`. The testcase compiles with
  the other `testbase/` files and the submission present.
- Marking is **headless** — see `grader-design.md`.

## Images

- Upload via `POST /files` with multipart field name **`attachment`**.
  The obvious `file` gets 400 "Missing attachment".
- The response id serves from `static.us.edusercontent.com/files/<id>`.
- `push-doc` does this automatically for local `![...](...)` refs.
  Re-pushing re-uploads; old file ids are orphaned, which is harmless.

## Runnable snippets in documents

- **A runnable ` ```java ` snippet is compiled as `Main.java`**
  regardless of the public class name inside it. Click Run on a snippet
  whose public class isn't literally `Main` and it fails with
  *"class X is public, should be declared in a file named X.java"*
  before the student's code even runs.
- `md_to_ed.py` auto-marks any snippet containing `void main(` as
  runnable. So: name that class `Main`, or force it off with
  ` ```java norun `.

## Guardrails in the tool

- Lesson titles must match `Lab|Homework|HW` and must not match
  `Midterm|Exam|Final|Quiz`. `--dev` overrides.
- A lesson titled **"Challenges"** matches no allowed pattern, so bonus
  challenges need `--dev` every time. Add `"Challenge"` to
  `allowed_lesson_patterns` in `config.yaml` to stop that.
- `--prod` cross-checks that the target lesson belongs to `prod_course`
  before touching anything.
- Nothing is ever pushed without `--no-dry-run`.

## When something looks wrong

1. `python3 ed_push.py doctor`
2. `python3 ed_push.py verify-challenge <dir>` — the ✗ rows name the
   exact field that didn't land.
3. Open the slide in Ed and press Test once with the reference solution
   pasted in.
