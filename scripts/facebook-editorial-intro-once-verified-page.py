"""Official Meta Graph: one reviewed, organic text post, with no POST retry."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

PAGE = "927870153743820"
VERSION = "v24.0"
BASE = "34769eba2da4af170ce825c7becc84b3fc235d8d"
RELEASE = Path(".github/releases/facebook-editorial-intro-2026-11-24-verified-page.json")
RELEASE_SHA256 = "25c86bf9d6adbff4ba39d36c5361c661b8195c3528affe975482f7c0307651b1"
POST_ID = re.compile(rf"{PAGE}_[0-9]+\Z")
UTC = dt.timezone.utc


class Stop(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def require(condition, message):
    if not condition:
        raise Stop(message)


def timestamp(value):
    require(isinstance(value, str) and 19 <= len(value) <= 35, "timestamp missing or invalid")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise Stop("timestamp missing or invalid") from None
    require(parsed.tzinfo is not None, "timestamp is not timezone-aware")
    return parsed.astimezone(UTC)


def to_json(stream):
    try:
        value = json.loads(stream.read(1024 * 1024 + 1))
    except (ValueError, TypeError):
        raise Stop("Graph response was not valid JSON") from None
    require(isinstance(value, dict), "Graph response did not contain an object")
    return value


def graph(opener, token, method, edge, query=None, form=None):
    url = f"https://graph.facebook.com/{VERSION}/{edge}"
    if query:
        url += "?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(
        url, method=method,
        data=urllib.parse.urlencode(form).encode() if form else None,
        headers={"Accept": "application/json", "Authorization": "Bearer " + token},
    )
    try:
        with opener.open(request, timeout=20) as response:
            result = to_json(response)
    except urllib.error.HTTPError as err:
        try:
            obj = to_json(err).get("error", {})
        except Stop:
            obj = {}
        if not isinstance(obj, dict):
            obj = {}
        code = obj.get("code")
        subcode = obj.get("error_subcode")
        safe = lambda value: value if type(value) is int else 0
        raise Stop(f"Graph {method} HTTP {err.code}, code {safe(code)}, subcode {safe(subcode)}") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise Stop(f"Graph {method} network or timeout error") from None
    require("error" not in result, f"Graph {method} returned an error object")
    return result


def check_context():
    require(os.environ.get("GITHUB_REPOSITORY") == "Troly2025/Verti", "wrong GitHub repository")
    require(os.environ.get("GITHUB_REF") == "refs/heads/main", "not main")
    require(os.environ.get("GITHUB_EVENT_NAME") == "push", "not the one-shot push")
    require(os.environ.get("GITHUB_RUN_ATTEMPT") == "1", "rerun blocked")
    sha = os.environ.get("GITHUB_SHA", "")
    require(re.fullmatch(r"[0-9a-f]{40}", sha) and sha != BASE, "missing release commit SHA")
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    require(event.get("before") == BASE and event.get("after") == sha
            and event.get("ref") == "refs/heads/main" and not event.get("forced"),
            "wrong GitHub push boundary")
    head = event.get("head_commit")
    require(isinstance(head, dict) and head.get("id") == sha, "missing exact head commit")
    age = dt.datetime.now(UTC) - timestamp(head.get("timestamp"))
    require(dt.timedelta(minutes=-5) <= age <= dt.timedelta(hours=8),
            "release push timestamp too old or in the future")
    data = RELEASE.read_bytes()
    require(hashlib.sha256(data).hexdigest() == RELEASE_SHA256, "reviewed release digest mismatch")
    marker = json.loads(data)
    require(marker.get("page_id") == PAGE and marker.get("api_version") == VERSION
            and marker.get("base_sha") == BASE, "marker Page, version, or base was not approved")
    message = marker.get("message")
    require(isinstance(message, str) and message.startswith("(English below)\n\n")
            and 100 <= len(message) <= 1800, "missing exact bilingual message")
    return message


def valid_permalink(value):
    if not isinstance(value, str) or len(value) > 600:
        return False
    try:
        url = urllib.parse.urlsplit(value)
        return (url.scheme == "https" and url.netloc in {"www.facebook.com", "facebook.com", "m.facebook.com"}
                and bool(url.path) and not url.fragment and not re.search(r"[\s<>`]", value))
    except ValueError:
        return False


def verify(call, post_id, message, since):
    require(isinstance(post_id, str) and POST_ID.fullmatch(post_id), "missing or wrong Page post ID")
    record = call("GET", post_id, query={"fields": "id,from,message,permalink_url,is_published,created_time"})
    author = record.get("from")
    require(record.get("id") == post_id and isinstance(author, dict) and author.get("id") == PAGE,
            "readback ID/author did not match target Page")
    require(record.get("is_published") is True, "Meta did not report is_published=true")
    require(record.get("message") == message, "published message did not match reviewed copy")
    created = timestamp(record.get("created_time"))
    require(since - dt.timedelta(seconds=60) <= created <= dt.datetime.now(UTC) + dt.timedelta(minutes=2),
            "post timestamp does not match the release window")
    link = record.get("permalink_url")
    require(valid_permalink(link), "Meta did not return a valid Facebook permalink")
    return created, link


def publish(call, message):
    me = call("GET", "me", query={"fields": "id,name"})
    require(me.get("id") == PAGE and isinstance(me.get("name"), str) and me["name"],
            "token is not for the exact target Page")
    feed = call("GET", f"{PAGE}/published_posts", query={"limit": 25, "fields": "id,message"})
    entries = feed.get("data")
    require(isinstance(entries, list) and all(isinstance(x, dict) for x in entries), "cannot check Page posts")
    require(not any(x.get("message") == message for x in entries), "exact copy already visible in Page feed; no write")
    started = dt.datetime.now(UTC)
    try:
        result = call("POST", f"{PAGE}/feed", form={"message": message, "published": "true"})
        post_id = result.get("id")
        created, link = verify(call, post_id, message, started)
    except Stop as err:
        raise Stop(f"POST was attempted; do not rerun or repost. Check the Page first. {err}") from None
    return post_id, created, link


def main():
    message = check_context()
    if sys.argv[1:] == ["--check"]:
        print("Local release, exact branch, timestamp, Page and Graph version checks passed.")
        return
    require(not sys.argv[1:], "invalid invocation")
    token = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", "")
    require(re.fullmatch(r"[A-Za-z0-9_.|-]{20,4096}", token),
            "missing or invalid-form Facebook Page environment secret")
    opener = urllib.request.build_opener(NoRedirect())
    post_id, created, link = publish(lambda *a, **k: graph(opener, token, *a, **k), message)
    proof = (f"Meta Page post ID: {post_id}\nCreated: {created.isoformat()}\n"
             f"Permalink: {link}\nMeta says published; independently check as a viewer without a Meta app role.\n")
    Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8").write(proof)
    print(proof, end="")


if __name__ == "__main__":
    try:
        main()
    except Stop as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except Exception:
        # Do not print tracebacks, requests, invocation arguments or response contents.
        print("Facebook one-shot stopped on an unexpected error. Do not rerun; review the Page before any new submission.", file=sys.stderr)
        sys.exit(1)
