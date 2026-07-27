# Troubleshooting

The sharp edges of Ed's undocumented API, in roughly the order you'll
meet them. Everything here was learned the hard way; the tool already
handles all of it — this file exists so a confusing symptom is
recognizable and so future maintainers don't re-discover the map.

## Requests

- **The API base is `https://us.edstem.org/api`** — not `/v1`, and
  note the `us.` region prefix (the docs and old blog posts you'll
  find online describe the Australian deployment; ids and hosts do
  not cross regions). The git remote, likewise, is
  `git.us.edstem.org`, not `git.edstem.org`.
- **403 from Cloudflare on every request?** Python's default
  User-Agent is blocked. Send any browser UA string (ed_api.py
  does). The sahara upload host needs it too.
- **Auth is `Authorization: Bearer <token>`** with an API token from
  Settings → API tokens. The browser itself uses a different header
  (`x-token` with a session JWT) — captures from devtools will show
  that; the Bearer token works on the same endpoints.

## Slides and challenges

- **Updating a challenge is `PATCH /challenges/{id}` with the FULL
  object** — GET it fresh, mutate, PATCH the whole thing back.
  `PUT` 404s, and sparse objects can drop sibling fields.
- **Updating a slide is `PUT /lessons/slides/{id}` with a
  FORM-ENCODED body** `slide=<json-string>` — a plain JSON body gets
  400 "Missing slide".
- **The lesson UI renders `slide.content`, not `challenge.content`**
  — write the description XML to BOTH or it silently doesn't show.
- **There is no create-slide endpoint** — new slides are made by
  CLONING a template: `POST /lessons/slides/{template}/clone` with
  `{lesson_id, is_hidden}`. Keep one blank code slide and one blank
  document slide as permanent templates.
- **The editor UI reads build/run commands from the tickets**
  (`tickets.run_standard.*`), not from `settings.*` — set both or
  the fields look empty in the UI while the API says they're set.
- **The "Workspace" checkbox is `features.full`**, not
  `features.connect` (connect can be true while the box is
  unchecked). Feedback visibility is `features.feedback`.
- **Lesson creation** (`POST /courses/{id}/lessons`) ignores the
  title in the body — create, then PUT the title back; new lessons
  arrive hidden as "Untitled Lesson".
- **Slide ids don't come out in a predictable order** when pushing a
  handout and a challenge back-to-back — never guess an id from the
  sequence; read `challenge_id` off the pushed slide.

## Filespaces (scaffold / solution / testbase / check)

- These have **no git or plain-REST door**. Uploads ride the
  workspace-ticket system: `POST /challenges/{id}/connect/{which}` →
  websocket to sahara (first frame carries the workspace id) →
  per-file upload tickets → multipart POST per file → finally PATCH
  the returned hash onto the challenge as `{which}_hash` to BIND it.
  Uploading without the binding PATCH changes nothing.
- **Uploads add or overwrite by filename — they never delete.**
  Remove a stray file through the Ed UI.
- `check` is a fourth filespace behind the "Check" button
  (`features.check` + `settings.check_command`), same protocol.

## Marking

- **`@Nested` JUnit classes render wrong** in Ed's results (at most
  one failure shown per nested class). Keep test classes flat.
- **Per-test points are `@Tag("score:N")`** (integers). Untagged
  tests score 1 point each regardless of the challenge's total.
- A broken submission that fails the build shows an "Errored" banner
  with the compiler output instead of test results — for debugging
  labs that's a feature, but don't mistake it for a grader crash.
- Ed provides JUnit 5 for `marking: unit`; the testcase compiles
  with the other testbase files and the submission present.

## Images

- Handout images upload via `POST /files` with multipart field name
  **`attachment`** (the obvious `file` gets 400 "Missing
  attachment"); the response id serves from
  `static.us.edusercontent.com/files/<id>`. `push-doc` does this
  automatically for local `![...](...)` references. Re-pushing
  re-uploads (old file ids are orphaned, which is harmless).

## Sanity checklist when something looks wrong

1. `python3 ed_push.py doctor`
2. `python3 ed_push.py verify-challenge <dir>` — the ✗ rows name the
   exact field that didn't land.
3. Open the slide in Ed and press Test once with the reference
   solution pasted in.
