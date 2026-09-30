"""Bounded unauthenticated GitHub Contents previews."""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import threading
import urllib.error
import urllib.parse
import urllib.request

from agentkit.contracts import ContractError

_API = "https://api.github.com/repos/"
_MAX_RESPONSE = 65_536
_MAX_SOURCE = 24_000
_MAX_SNAPSHOT = 32_768
_SEM = threading.BoundedSemaphore(2)
_SEGMENT = re.compile(r"^[^\x00-\x1f\x7f/\\]+$")
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        fp.close()
        raise ContractError("GitHub redirect is not allowed.")


def _validate(payload: dict) -> tuple[str, str, str, str, str]:
    if not isinstance(payload, dict) or set(payload) != {"owner", "repo", "path", "ref"}:
        raise ContractError("GitHub preview requires exactly owner, repo, path and ref.")
    owner, repo, path, ref = (payload[key] for key in ("owner", "repo", "path", "ref"))
    if not all(isinstance(value, str) for value in (owner, repo, path, ref)):
        raise ContractError("GitHub preview fields must be text.")
    if not owner or not repo or len(owner) > 100 or len(repo) > 100 or owner in {".", ".."} or repo in {".", ".."} or not re.fullmatch(r"[A-Za-z0-9-]+", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]+", repo):
        raise ContractError("Invalid GitHub owner or repository.")
    segments = path.split("/")
    if not path or len(path) > 500 or any(not segment or segment in {".", ".."} or not _SEGMENT.fullmatch(segment) for segment in segments):
        raise ContractError("Invalid GitHub relative path.")
    if not ref or len(ref) > 200 or any(ord(char) < 32 or ord(char) == 127 for char in ref):
        raise ContractError("Invalid GitHub ref.")
    if ref.startswith("/") or "\\" in ref:
        raise ContractError("Invalid GitHub ref.")
    encoded_path = "/".join(urllib.parse.quote(segment, safe="") for segment in segments)
    url = _API + owner + "/" + repo + "/contents/" + encoded_path + "?ref=" + urllib.parse.quote(ref, safe="/")
    return owner, repo, path, ref, url


def _error_for(exc: Exception) -> ContractError:
    if isinstance(exc, ContractError):
        return exc
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code == 404:
            return ContractError("GitHub file was not found.")
        if exc.code in (403, 429):
            return ContractError("GitHub rate limit or access restriction.")
        return ContractError("GitHub request failed.")
    if isinstance(exc, (urllib.error.URLError, TimeoutError, OSError)):
        return ContractError("GitHub network request failed.")
    return ContractError("GitHub response was invalid.")


def preview_file(payload: dict) -> dict:
    owner, repo, path, ref, url = _validate(payload)
    if not _SEM.acquire(blocking=False):
        raise ContractError("GitHub preview concurrency limit reached.")
    try:
        request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "AI-Studio-public-preview"})
        response = None
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
            response = opener.open(request, timeout=10)
            raw = response.read(_MAX_RESPONSE + 1)
            if len(raw) > _MAX_RESPONSE:
                raise ContractError("GitHub response is too large.")
            value = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            if isinstance(exc, urllib.error.HTTPError):
                exc.close()
            raise _error_for(exc) from exc
        finally:
            if response is not None and hasattr(response, "close"):
                response.close()
        if not isinstance(value, dict) or value.get("type") != "file" or value.get("path") != path or value.get("name") != path.rsplit("/", 1)[-1] or value.get("encoding") != "base64" or "submodule_git_url" in value:
            raise ContractError("GitHub response is not a regular file.")
        encoded = value.get("content")
        if not isinstance(encoded, str):
            raise ContractError("GitHub file content is invalid.")
        try:
            data = base64.b64decode(re.sub(r"\s+", "", encoded), validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ContractError("GitHub file content is invalid.") from exc
        if len(data) > _MAX_SOURCE or type(value.get("size")) is not int or value["size"] != len(data):
            raise ContractError("GitHub file is too large.")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ContractError("GitHub file is not UTF-8 text.") from exc
        if "\x00" in text:
            raise ContractError("GitHub file contains NUL bytes.")
        blob_sha = value.get("sha")
        expected = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if not isinstance(blob_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", blob_sha) or blob_sha != expected:
            raise ContractError("GitHub blob integrity check failed.")
        source_path = "/".join(urllib.parse.quote(segment, safe="") for segment in path.split("/"))
        source_url = "https://github.com/" + owner + "/" + repo + "/blob/" + urllib.parse.quote(ref, safe="") + "/" + source_path
        header = f"GitHub source: {owner}/{repo}@{ref} {path} (blob {blob_sha})\nSource URL: {source_url}\n\n"
        snapshot = (header + text).encode("utf-8")
        if len(snapshot) > _MAX_SNAPSHOT:
            raise ContractError("GitHub snapshot is too large.")
        base = _SAFE.sub("-", path.rsplit("/", 1)[-1]).strip("-") or "file"
        name = "github-" + base[: max(1, 120 - len("github-") - len(".txt"))] + ".txt"
        return {"name": name, "size": len(snapshot), "content_base64": base64.b64encode(snapshot).decode("ascii"),
                "text": snapshot.decode("utf-8"), "source": {"owner": owner, "repo": repo, "path": path, "ref": ref, "blob_sha": blob_sha, "url": source_url}}
    finally:
        _SEM.release()
