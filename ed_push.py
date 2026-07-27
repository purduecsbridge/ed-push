#!/usr/bin/env python3
"""ed_push.py — push a complete Ed code challenge from a source directory.

A challenge directory looks like:

    my-challenge/
      challenge.yaml     manifest (see example-challenge/)
      writeup.md         the student-facing description
      scaffold/          exactly the files students start with
      solution/          the reference solution files
      testbase/          the JUnit tests (+ any harness files they need)

Commands:
    python3 ed_push.py doctor                       # is my setup working?
    python3 ed_push.py convert path/to/writeup.md   # preview the Ed XML
    python3 ed_push.py push-challenge my-challenge/ # dry-run by default
    python3 ed_push.py push-challenge my-challenge/ --no-dry-run

Reads config.yaml next to this script (course id, template slide,
lesson-title guardrails). Auth: your own Ed API token via ED_API_TOKEN or
~/.config/ed/token.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

from ed_api import need_token, put_slide, request, upload_file, upload_workspace_files
from md_to_ed import markdown_to_ed_xml, png_size

HERE = Path(__file__).resolve().parent


def load_config() -> dict:
    f = HERE / "config.yaml"
    if not f.is_file():
        raise SystemExit(f"missing {f} — copy config.yaml.example and fill it in")
    return yaml.safe_load(f.read_text())


def load_manifest(chdir: Path) -> dict:
    f = chdir / "challenge.yaml"
    if not f.is_file():
        raise SystemExit(f"missing {f}")
    man = yaml.safe_load(f.read_text())
    required = ["title", "lesson", "build_command", "run_command"]
    if man.get("marking", "unit") == "unit":
        required += ["points", "testcase_file"]
    for key in required:
        if key not in man:
            raise SystemExit(f"challenge.yaml is missing required key: {key}")
    return man


def guard_lesson(cfg: dict, token: str, lesson_id: int, force: bool) -> None:
    """Refuse lessons whose titles look like assessments unless --force."""
    lesson = request("GET", f"/lessons/{lesson_id}", token)
    title = lesson.get("lesson", lesson).get("title", "")
    blocked = cfg.get("blocked_lesson_patterns") or []
    allowed = cfg.get("allowed_lesson_patterns") or []
    if any(re.search(p, title, re.I) for p in blocked) and not force:
        raise SystemExit(f'lesson {lesson_id} "{title}" matches a blocked pattern '
                         f"({blocked}); this tool is for labs/HW — use --force only "
                         "if you are certain")
    if allowed and not any(re.search(p, title, re.I) for p in allowed) and not force:
        raise SystemExit(f'lesson {lesson_id} "{title}" matches no allowed pattern '
                         f"({allowed}); use --force to override")
    print(f'lesson {lesson_id}: "{title}" — ok')


def workspace_files(chdir: Path, which: str) -> list[Path]:
    d = chdir / which
    if not d.is_dir():
        return []
    return sorted(p for p in d.iterdir() if p.is_file())


def cmd_doctor(args):
    token = need_token()
    cfg = load_config()
    user = request("GET", "/user", token)
    name = user.get("user", user).get("name", "?")
    print(f"token ok: acting as {name}")
    course = cfg.get("course")
    lessons = request("GET", f"/courses/{course}/lessons", token)
    n = len(lessons.get("lessons", []))
    print(f"course {course}: reachable ({n} lessons)")
    try:
        import websocket  # noqa: F401
        print("websocket-client: installed")
    except ImportError:
        print("websocket-client: MISSING — pip install websocket-client")
    print("doctor: all good" if n else "doctor: check course id")


def cmd_convert(args):
    print(markdown_to_ed_xml(Path(args.file).read_text()))


def make_slide(cfg: dict, token: str, lesson_id: int, title: str,
               template: int | None = None, hidden: bool = False) -> dict:
    """Create a fresh code slide by cloning a template slide (the
    manifest's template_slide if given, else the configured one).
    Slides are VISIBLE by default; pass hidden=True (manifest
    `hidden: true`) for e.g. exam slides."""
    template = template or cfg.get("template_slide")
    if not template:
        raise SystemExit("no slide id in challenge.yaml and no template_slide in "
                         "config.yaml — create the slide in the Ed UI and put its "
                         "id in challenge.yaml, or configure a template")
    resp = request("POST", f"/lessons/slides/{template}/clone", token,
                   {"lesson_id": lesson_id, "is_hidden": hidden})
    slide = resp.get("slide", resp)
    state = "hidden" if hidden else "visible"
    print(f"cloned template {template} -> slide {slide['id']} ({state}) in lesson {lesson_id}")
    return slide


def make_image_uploader(base: Path, token: str | None, dry: bool):
    """image_uploader callback for markdown_to_ed_xml: resolves local
    image paths against `base`, uploads each once, returns (url, w, h)."""
    cache: dict[str, tuple] = {}

    def upload(src: str):
        if src in cache:
            return cache[src]
        p = (base / src).resolve()
        if not p.is_file():
            raise SystemExit(f"image not found: {p} (referenced as {src!r})")
        dims = png_size(p.read_bytes()) or (None, None)
        if dry:
            result = (f"dry-run://{src}", *dims)
        else:
            url = upload_file(p, token)
            print(f"  image: uploaded {src} -> {url}")
            result = (url, *dims)
        cache[src] = result
        return result

    return upload


def cmd_push_challenge(args):
    token = need_token()
    cfg = load_config()
    chdir = Path(args.dir).resolve()
    man = load_manifest(chdir)
    dry = args.dry_run

    guard_lesson(cfg, token, man["lesson"], args.force)

    # --- slide: existing or cloned from the template ---
    if man.get("slide"):
        slide = request("GET", f"/lessons/slides/{man['slide']}", token)["slide"]
    elif dry:
        print("dry-run: would clone the template slide (no slide id in manifest)")
        slide = None
    else:
        slide = make_slide(cfg, token, man["lesson"], man["title"],
                           man.get("template_slide"),
                           hidden=bool(man.get("hidden", False)))
    challenge_id = slide.get("challenge_id") if slide else None
    if slide and not challenge_id:
        raise SystemExit(f"slide {slide['id']} has no challenge_id — is the template a code slide?")

    content = markdown_to_ed_xml((chdir / "writeup.md").read_text(),
                                 make_image_uploader(chdir, token, dry))
    scaffold = workspace_files(chdir, "scaffold")
    solution = workspace_files(chdir, "solution")
    testbase = workspace_files(chdir, "testbase")
    check = workspace_files(chdir, "check")
    if check and not man.get("check_command"):
        raise SystemExit("check/ files present but no check_command in challenge.yaml")
    tb_names = [p.name for p in testbase]
    unit_marked = man.get("marking", "unit") == "unit"
    if unit_marked and man["testcase_file"] not in tb_names:
        raise SystemExit(f'testcase_file "{man["testcase_file"]}" is not in testbase/ ({tb_names})')

    print(f"challenge: {man['title']}  ({len(content)} chars of description)")
    print(f"  scaffold: {[p.name for p in scaffold]}")
    print(f"  solution: {[p.name for p in solution]}")
    print(f"  testbase: {tb_names}")
    if check:
        print(f"  check:    {[p.name for p in check]}  ({man['check_command']})")
    if dry:
        print("dry-run: nothing pushed. Re-run with --no-dry-run to push.")
        return

    # --- challenge object: content, marking, settings ---
    ch = request("GET", f"/challenges/{challenge_id}", token)["challenge"]
    ch["content"] = content
    ch["settings"]["build_command"] = man["build_command"]
    ch["settings"]["run_command"] = man["run_command"]
    # The UI reads the commands from the TICKETS, not settings (found by
    # diffing a hand-configured challenge 2026-07-26): run_standard powers
    # the Run button and the editor's Build/Run fields; the UI mirrors the
    # build command into the other mark tickets too.
    tk = ch["tickets"]
    tk["run_standard"]["build_command"] = man["build_command"]
    tk["run_standard"]["run_command"] = man["run_command"]
    for t in ("mark_standard", "mark_custom"):
        if t in tk:
            tk[t]["build_command"] = man["build_command"]
    if unit_marked:
        ch["type"] = "unit"
        ch["auto_points"] = man["points"]
        ch["settings"]["per_testcase_scores"] = bool(man.get("per_testcase_scores", True))
        mark = ch["tickets"]["mark_unit"]
        mark["testcase_path"] = man["testcase_file"]
        mark["build_command"] = man["build_command"]
        ms = int(man.get("time_limit_seconds", 60)) * 1000
        mark["run_limit"]["wall_time"] = ms
        mark["run_limit"]["cpu_time"] = ms
    # marking: none (demos) or other types: files/commands/content only;
    # configure special marking (e.g. Ed's "code" type) in the UI.
    ch["features"]["git_submission"] = bool(man.get("git_submission", False))
    if "workspace" in man:   # the "Workspace" box = features.full (the
        # hand-configured reference has full=True AND connect=True;
        # connect alone does NOT check the box — verified 2026-07-26)
        ch["features"]["full"] = bool(man["workspace"])
        ch["features"]["connect"] = bool(man["workspace"])
    # students see test output / feedback (hand-configured references have
    # this ON; without it a failed Test shows nothing useful)
    ch["features"]["feedback"] = bool(man.get("feedback", True))
    # advisory style checker: the "Check" box opens a fourth filespace
    # (check/) and runs settings.check_command against the submission
    if man.get("check_command"):
        ch["features"]["check"] = True
        ch["settings"]["check_command"] = man["check_command"]
    if "attempts" in man:    # attempts allowed per interval (UI default 10)
        ch["attempts_within_last_interval"] = int(man["attempts"])
    request("PATCH", f"/challenges/{challenge_id}", token, {"challenge": ch})
    print("  challenge settings + description: pushed")

    # --- slide: title + the same description ---
    slide["title"] = man["title"]
    slide["content"] = content
    put_slide(slide["id"], slide, token)
    print("  slide title + description: pushed")

    # --- the four workspaces ---
    for which, files in (("scaffold", scaffold), ("solution", solution),
                         ("testbase", testbase), ("check", check)):
        if files:
            upload_workspace_files(challenge_id, which, files, token)

    ok = verify_challenge(token, man, challenge_id, slide["id"],
                          expect_scaffold=bool(scaffold),
                          expect_solution=bool(solution),
                          expect_testbase=bool(testbase),
                          expect_check=bool(check))
    print(f"  slide {slide['id']}  challenge {challenge_id}")
    if ok:
        print("VERIFY: all fields ✓. Open the slide in Ed, eyeball the "
              "description, and click Test once.")
    else:
        print("VERIFY: MISMATCHES ABOVE — fix and re-push before using "
              "this challenge.")
        raise SystemExit(1)


def verify_challenge(token, man, challenge_id, slide_id,
                     expect_scaffold=True, expect_solution=True,
                     expect_testbase=True, expect_check=False) -> bool:
    """GET the pushed challenge + slide back and assert every
    manifest-driven field actually landed. Returns True if clean."""
    ch = request("GET", f"/challenges/{challenge_id}", token)["challenge"]
    slide = request("GET", f"/lessons/slides/{slide_id}", token)["slide"]
    mu = ch.get("tickets", {}).get("mark_unit") or {}
    unit = man.get("marking", "unit") == "unit"

    rs = ch.get("tickets", {}).get("run_standard") or {}
    checks = [
        ("settings.build_command", ch["settings"].get("build_command"), man["build_command"]),
        ("settings.run_command", ch["settings"].get("run_command"), man["run_command"]),
        ("run_standard.build_command (UI)", rs.get("build_command"), man["build_command"]),
        ("run_standard.run_command (UI)", rs.get("run_command"), man["run_command"]),
        ("features.full (workspace box)", ch["features"].get("full"),
         bool(man.get("workspace", ch["features"].get("full")))),
        ("features.connect", ch["features"].get("connect"),
         bool(man.get("workspace", ch["features"].get("connect")))),
        ("features.git_submission", ch["features"].get("git_submission"),
         bool(man.get("git_submission", False))),
        ("features.feedback", ch["features"].get("feedback"),
         bool(man.get("feedback", True))),
        ("slide.title", slide.get("title"), man["title"]),
        ("slide.content == challenge.content",
         slide.get("content") == ch.get("content"), True),
    ]
    if man.get("check_command"):
        checks += [
            ("features.check", ch["features"].get("check"), True),
            ("settings.check_command", ch["settings"].get("check_command"),
             man["check_command"]),
        ]
    if unit:
        ms = int(man.get("time_limit_seconds", 60)) * 1000
        checks += [
            ("type", ch.get("type"), "unit"),
            ("auto_points", ch.get("auto_points"), man["points"]),
            ("settings.per_testcase_scores", ch["settings"].get("per_testcase_scores"),
             bool(man.get("per_testcase_scores", True))),
            ("mark_unit.testcase_path", mu.get("testcase_path"), man["testcase_file"]),
            ("mark_unit.build_command", mu.get("build_command"), man["build_command"]),
            ("mark_unit.run_limit.wall_time", (mu.get("run_limit") or {}).get("wall_time"), ms),
        ]
    for which, expected in (("scaffold", expect_scaffold),
                            ("solution", expect_solution),
                            ("testbase", expect_testbase),
                            ("check", expect_check)):
        if expected:
            checks.append((f"{which}_hash bound",
                           bool(ch.get(f"{which}_hash")), True))

    ok = True
    print("  verify:")
    for name, actual, expected in checks:
        good = actual == expected
        ok &= good
        mark = "✓" if good else "✗"
        detail = "" if good else f"  (got {actual!r}, wanted {expected!r})"
        print(f"    {mark} {name}{detail}")
    return ok


def cmd_push_doc(args):
    """Push a markdown file as a DOCUMENT slide (e.g. a lab handout).
    Reuse an existing slide with --slide, or clone --template (a blank
    document slide) into --lesson. Prints the new slide id — record it
    and use --slide for every later re-push."""
    token = need_token()
    cfg = load_config()
    src = Path(args.file)
    md = src.read_text()
    content = markdown_to_ed_xml(md, make_image_uploader(src.parent, token,
                                                         args.dry_run))
    m = re.search(r"^#\s+(.+)$", md, re.M)
    title = args.title or (m.group(1).strip() if m else Path(args.file).stem)

    if args.slide:
        slide = request("GET", f"/lessons/slides/{args.slide}", token)["slide"]
        print(f'slide {slide["id"]} ("{slide.get("title")}", type {slide.get("type")}): reusing')
    elif not args.lesson:
        raise SystemExit("need --slide (reuse) or --lesson (clone the template into it)")
    else:
        guard_lesson(cfg, token, args.lesson, args.force)
        slide = None

    print(f'doc: "{title}"  ({len(content)} chars of XML from {args.file})')
    if args.dry_run:
        print("dry-run: nothing pushed. Re-run with --no-dry-run to push.")
        return
    if slide is None:
        template = args.template or cfg.get("doc_template_slide")
        if not template:
            raise SystemExit("no --template and no doc_template_slide in "
                             "config.yaml — designate a blank DOCUMENT slide "
                             "to clone (the code template won't do)")
        slide = make_slide(cfg, token, args.lesson, title, template,
                           hidden=args.hidden)
    slide["title"] = title
    slide["content"] = content
    put_slide(slide["id"], slide, token)

    back = request("GET", f"/lessons/slides/{slide['id']}", token)["slide"]
    ok = back.get("title") == title and back.get("content") == content
    print(f"  slide {slide['id']}: pushed, round-trip "
          + ("✓" if ok else "✗ MISMATCH — inspect in Ed"))
    print(f"  (record it: re-push later with --slide {slide['id']})")
    if not ok:
        raise SystemExit(1)


def cmd_verify_challenge(args):
    """Standalone re-verification: reads the manifest, finds the slide's
    challenge, and runs the same post-push field checks."""
    token = need_token()
    chdir = Path(args.dir).resolve()
    man = load_manifest(chdir)
    if not man.get("slide"):
        raise SystemExit("manifest has no slide: id — verify needs the pushed "
                         "slide id (add it after the first push)")
    slide = request("GET", f"/lessons/slides/{man['slide']}", token)["slide"]
    cid = slide.get("challenge_id")
    if not cid:
        raise SystemExit(f"slide {man['slide']} has no challenge_id")
    has = lambda w: (chdir / w).is_dir() and any((chdir / w).iterdir())
    ok = verify_challenge(token, man, cid, slide["id"],
                          expect_scaffold=has("scaffold"),
                          expect_solution=has("solution"),
                          expect_testbase=has("testbase"),
                          expect_check=has("check"))
    print(f"challenge {cid} / slide {slide['id']}: "
          + ("all fields ✓" if ok else "MISMATCHES — see above"))
    raise SystemExit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("doctor", help="check token, course access, dependencies")
    p.set_defaults(fn=cmd_doctor)

    p = sub.add_parser("convert", help="print a writeup.md as Ed XML (preview)")
    p.add_argument("file")
    p.set_defaults(fn=cmd_convert)

    p = sub.add_parser("push-challenge", help="push a challenge directory to Ed")
    p.add_argument("dir")
    p.add_argument("--dry-run", dest="dry_run", action="store_true", default=True)
    p.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    p.add_argument("--force", action="store_true",
                   help="override the lesson-title guardrails")
    p.set_defaults(fn=cmd_push_challenge)

    p = sub.add_parser("push-doc",
                       help="push a markdown file as a document slide (handouts)")
    p.add_argument("file")
    p.add_argument("--slide", type=int, help="existing document slide to update")
    p.add_argument("--lesson", type=int, help="lesson to clone the template into")
    p.add_argument("--template", type=int,
                   help="blank DOCUMENT slide to clone (default: config "
                        "doc_template_slide)")
    p.add_argument("--title", help="slide title (default: first # heading)")
    p.add_argument("--hidden", action="store_true",
                   help="create the slide hidden (visible is the default)")
    p.add_argument("--dry-run", dest="dry_run", action="store_true", default=True)
    p.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    p.add_argument("--force", action="store_true",
                   help="override the lesson-title guardrails")
    p.set_defaults(fn=cmd_push_doc)

    p = sub.add_parser("verify-challenge",
                       help="re-check a previously pushed challenge against its manifest")
    p.add_argument("dir")
    p.set_defaults(fn=cmd_verify_challenge)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
