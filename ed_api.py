"""Ed API helpers: token, REST requests, slide save, workspace uploads.

Self-contained (no dependency on lectures/ed) so this directory can be
lifted into its own repo for TA use.

Auth: an Ed API token from edstem.org -> Settings -> API tokens, supplied
via the ED_API_TOKEN environment variable or a file at ~/.config/ed/token.
The token acts as YOU: use your own, never a shared one.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

API = "https://us.edstem.org/api"
SAHARA = "https://sahara.us.edstem.org"
SAHARA_WS = "wss://sahara.us.edstem.org/connect"
# Cloudflare 403s python's default User-Agent; any browser UA works.
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"


def need_token() -> str:
    tok = os.environ.get("ED_API_TOKEN")
    if not tok:
        f = Path.home() / ".config" / "ed" / "token"
        if f.is_file():
            tok = f.read_text().strip()
    if not tok:
        raise SystemExit("no Ed token: export ED_API_TOKEN=... or put it in ~/.config/ed/token")
    return tok


def request(method: str, path: str, token: str, body: dict | None = None) -> dict:
    """JSON request against the Ed REST API."""
    req = urllib.request.Request(API + path, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("User-Agent", UA)
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, data) as r:
        text = r.read()
    return json.loads(text) if text else {}


def put_slide(slide_id: int, slide: dict, token: str) -> None:
    """Slides update via PUT with a FORM-ENCODED slide=<json> body
    (a plain JSON body gets 400 "Missing slide")."""
    req = urllib.request.Request(f"{API}/lessons/slides/{slide_id}",
                                 data=urllib.parse.urlencode({"slide": json.dumps(slide)}).encode(),
                                 method="PUT")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("User-Agent", UA)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    urllib.request.urlopen(req).read()


def upload_file(path: Path, token: str) -> str:
    """Upload an image/attachment to Ed's file store and return its public
    URL. Endpoint discovered 2026-07-26: POST /files, multipart field
    "attachment" -> 201 {"file": {"id": ...}}; the file then serves from
    static.us.edusercontent.com/files/<id> (round-trip verified)."""
    content = path.read_bytes()
    boundary = uuid.uuid4().hex
    ctype = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
             "gif": "image/gif", "svg": "image/svg+xml"}.get(
        path.suffix.lstrip(".").lower(), "application/octet-stream")
    body = ((f"--{boundary}\r\n"
             f'Content-Disposition: form-data; name="attachment"; filename="{path.name}"\r\n'
             f"Content-Type: {ctype}\r\n\r\n").encode()
            + content + f"\r\n--{boundary}--\r\n".encode())
    req = urllib.request.Request(API + "/files", data=body, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("User-Agent", UA)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req) as r:
        file_id = json.loads(r.read())["file"]["id"]
    return f"https://static.us.edusercontent.com/files/{file_id}"


def upload_workspace_files(challenge_id: int, which: str, files: list[Path],
                           token: str, bind: bool = True) -> str:
    """Upload files into a challenge workspace (scaffold/solution/testbase)
    and bind the resulting hash to the challenge.

    Protocol (captured from the challenge editor 2026-07-19, verified):
      1. POST /challenges/{id}/connect/{which}          -> sahara WS ticket
      2. WS connect: the first frame ("init") carries the workspace wid
      3. POST /workspaces/{wid}/upload                  -> one-time upload ticket
      4. POST sahara /upload/{ticket}, multipart "file" -> workspace hash
         (repeat 3-4 per file; the hash accumulates)
      5. PATCH /challenges/{id} with {which}_hash       -> binds the state
    """
    import websocket  # deferred so the REST-only commands work without it

    ticket = request("POST", f"/challenges/{challenge_id}/connect/{which}", token,
                     {"user_id": None, "password": None, "i": None})["ticket"]
    ws = websocket.create_connection(SAHARA_WS + "?ticket=" + ticket,
                                     origin="https://edstem.org", timeout=15)
    try:
        wid = json.loads(ws.recv())["data"]["wid"]
        final_hash = None
        for p in files:
            content = p.read_bytes()
            up = request("POST", f"/workspaces/{wid}/upload", token,
                         {"wid": wid, "path": "/home/dummy"})["ticket"]
            boundary = uuid.uuid4().hex
            body = ((f"--{boundary}\r\n"
                     f'Content-Disposition: form-data; name="file"; filename="{p.name}"\r\n'
                     "Content-Type: application/octet-stream\r\n\r\n").encode()
                    + content + f"\r\n--{boundary}--\r\n".encode())
            req = urllib.request.Request(f"{SAHARA}/upload/{up}", data=body, method="POST")
            req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
            req.add_header("Origin", "https://edstem.org")
            req.add_header("User-Agent", UA)   # Cloudflare 403s python's default UA
            with urllib.request.urlopen(req) as r:
                final_hash = json.loads(r.read())["hash"]
            print(f"    {which}: uploaded {p.name} ({len(content)} bytes)")
    finally:
        ws.close()

    if bind and final_hash:
        ch = request("GET", f"/challenges/{challenge_id}", token)["challenge"]
        ch[f"{which}_hash"] = final_hash
        request("PATCH", f"/challenges/{challenge_id}", token, {"challenge": ch})
        stored = request("GET", f"/challenges/{challenge_id}", token)["challenge"].get(f"{which}_hash")
        ok = stored and final_hash.startswith(stored.split(":::")[0])
        print(f"    {which}: hash bound, verified={bool(ok)}")
    return final_hash or ""
