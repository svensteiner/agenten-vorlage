import base64
import hashlib
import json
import unittest
import urllib.error
import os
from unittest.mock import patch

from agentkit.contracts import ContractError
from cockpit.github_connector import preview_file


class Response:
    def __init__(self, body):
        self.body = body
        self.closed = False

    def read(self, limit=-1):
        return self.body if limit < 0 else self.body[:limit]

    def close(self):
        self.closed = True


def payload(path="src/Grüße.txt", data=b"hello"):
    sha = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    return {"type": "file", "path": path, "name": path.rsplit("/", 1)[-1], "size": len(data), "encoding": "base64", "content": base64.b64encode(data).decode(), "sha": sha}


class GitHubConnectorTests(unittest.TestCase):
    def test_unicode_preview_hash_source_and_no_auth(self):
        response = json.dumps(payload()).encode()
        seen = []
        responses = []
        def opener(_self, request, timeout):
            seen.append(request)
            value = Response(response)
            responses.append(value)
            return value
        with patch("urllib.request.build_opener", return_value=type("O", (), {"open": opener})()):
            result = preview_file({"owner": "octo", "repo": "repo", "path": "src/Grüße.txt", "ref": "refs/heads/main"})
        self.assertIn("GitHub source: octo/repo@refs/heads/main", result["text"])
        self.assertEqual(result["size"], len(result["text"].encode()))
        self.assertNotIn("Authorization", seen[0].headers)
        self.assertTrue(responses[0].closed)

    def test_invalid_inputs_do_not_network(self):
        with patch("urllib.request.build_opener") as build:
            for item in ({"owner": "..", "repo": "x", "path": "a", "ref": "main"},
                         {"owner": "o", "repo": "r", "path": "../a", "ref": "main"},
                         {"owner": "o", "repo": "r", "path": "a\\b", "ref": "main"},
                         {"owner": "o", "repo": "r", "path": "a", "ref": ""},
                         {"owner": "o", "repo": "r", "path": "a", "ref": "main", "extra": 1}):
                with self.assertRaises(ContractError):
                    preview_file(item)
            build.assert_not_called()

    def test_malformed_directory_binary_and_wrong_hash(self):
        for value in ({"type": "dir"}, {**payload(), "content": base64.b64encode(b"a\0b").decode()}, {**payload(), "sha": "0" * 40}):
            with patch("urllib.request.build_opener", return_value=type("O", (), {"open": lambda _self, request, timeout, value=value: Response(json.dumps(value).encode())})()):
                with self.assertRaises(ContractError):
                    preview_file({"owner": "o", "repo": "r", "path": "src/Grüße.txt", "ref": "main"})

    def test_http_limits_statuses_redirect_and_semaphore_release(self):
        with patch("urllib.request.build_opener", return_value=type("O", (), {"open": lambda *_args, **_kwargs: Response(b"x" * 65537)})()):
            with self.assertRaises(ContractError):
                preview_file({"owner": "o", "repo": "r", "path": "a", "ref": "main"})

    def test_redirect_proxy_and_headers_are_rejected_or_clean(self):
        import cockpit.github_connector as module
        with self.assertRaises(ContractError):
            module._NoRedirect().redirect_request(None, type("F", (), {"close": lambda _self: None})(), 302, "Found", {}, "https://evil.example")
        captured = []
        response = Response(json.dumps(payload(path="a")).encode())
        class Opener:
            def open(self, request, timeout):
                captured.append(request)
                return response
        def build(*handlers):
            self.assertTrue(any(isinstance(item, urllib.request.ProxyHandler) and item.proxies == {} for item in handlers))
            self.assertTrue(any(isinstance(item, module._NoRedirect) for item in handlers))
            return Opener()
        with patch.dict(os.environ, {"GH_TOKEN": "secret", "HTTPS_PROXY": "http://secret"}), patch("urllib.request.build_opener", side_effect=build):
            preview_file({"owner": "o", "repo": "r", "path": "a", "ref": "main"})
        self.assertNotIn("Authorization", captured[0].headers)
        self.assertNotIn("Cookie", captured[0].headers)
        self.assertEqual("2022-11-28", captured[0].headers["X-github-api-version"])

    def test_bounds_metadata_and_text_rejections(self):
        for size in (24_000, 24_001):
            data = b"a" * size
            value = payload(path="a", data=data)
            with patch("urllib.request.build_opener", return_value=type("O", (), {"open": lambda _self, request, timeout, value=value: Response(json.dumps(value).encode())})()):
                if size == 24_000:
                    result = preview_file({"owner": "o", "repo": "r", "path": "a", "ref": "main"})
                    self.assertLessEqual(result["size"], 32_768)
                    self.assertTrue(result["text"].endswith("a" * size))
                else:
                    with self.assertRaises(ContractError):
                        preview_file({"owner": "o", "repo": "r", "path": "a", "ref": "main"})
        for data in (b"\xff", b"a\0b"):
            value = payload(path="a", data=data)
            with patch("urllib.request.build_opener", return_value=type("O", (), {"open": lambda _self, request, timeout, value=value: Response(json.dumps(value).encode())})()):
                with self.assertRaises(ContractError):
                    preview_file({"owner": "o", "repo": "r", "path": "a", "ref": "main"})
        for field, value in (("name", "wrong"), ("size", 99), ("sha", "0" * 40)):
            item = payload(path="a")
            item[field] = value
            with patch("urllib.request.build_opener", return_value=type("O", (), {"open": lambda _self, request, timeout, item=item: Response(json.dumps(item).encode())})()):
                with self.assertRaises(ContractError):
                    preview_file({"owner": "o", "repo": "r", "path": "a", "ref": "main"})
        long_name = "a" * 500
        value = payload(path=long_name, data=b"ok")
        with patch("urllib.request.build_opener", return_value=type("O", (), {"open": lambda _self, request, timeout: Response(json.dumps(value).encode())})()):
            result = preview_file({"owner": "o", "repo": "r", "path": long_name, "ref": "main"})
        self.assertLessEqual(len(result["name"]), 120)
        self.assertTrue(result["name"].endswith(".txt"))

    def test_length_validation_never_networks(self):
        with patch("urllib.request.build_opener") as build:
            for key, value in (("owner", "o" * 101), ("repo", "r" * 101), ("path", "a" * 501)):
                item = {"owner": "o", "repo": "r", "path": "a", "ref": "main"}
                item[key] = value
                with self.assertRaises(ContractError):
                    preview_file(item)
            build.assert_not_called()

    def test_semaphore_releases_on_json_and_response_errors(self):
        import cockpit.github_connector as module
        bad = Response(b"not-json")
        good = Response(json.dumps(payload(path="a")).encode())
        opener = type("O", (), {"open": lambda _self, request, timeout: bad})()
        with patch("urllib.request.build_opener", return_value=opener):
            with self.assertRaises(ContractError):
                preview_file({"owner": "o", "repo": "r", "path": "a", "ref": "main"})
        opener.open = lambda request, timeout: good
        with patch("urllib.request.build_opener", return_value=opener):
            self.assertEqual("hello", preview_file({"owner": "o", "repo": "r", "path": "a", "ref": "main"})["text"].split("\n\n", 1)[1])
        self.assertTrue(bad.closed and good.closed)
        acquired = 0
        try:
            for _ in range(2):
                if module._SEM.acquire(blocking=False):
                    acquired += 1
            self.assertEqual(2, acquired)
        finally:
            for _ in range(acquired):
                module._SEM.release()

    def test_http_status_and_network_errors_are_generic(self):
        for error in (urllib.error.HTTPError("https://api.github.com", 404, "private-secret-body", {}, None),
                      urllib.error.HTTPError("https://api.github.com", 429, "rate-secret", {}, None),
                      urllib.error.URLError("proxy-secret")):
            with patch("urllib.request.build_opener", side_effect=error):
                with self.assertRaises(ContractError) as raised:
                    preview_file({"owner": "o", "repo": "r", "path": "a", "ref": "main"})
                self.assertNotIn("secret", str(raised.exception))

    def test_concurrency_limit(self):
        import cockpit.github_connector as module
        acquired = 0
        try:
            for _ in range(2):
                self.assertTrue(module._SEM.acquire(blocking=False))
                acquired += 1
            with self.assertRaises(ContractError):
                preview_file({"owner": "o", "repo": "r", "path": "a", "ref": "main"})
        finally:
            for _ in range(acquired):
                module._SEM.release()


if __name__ == "__main__":
    unittest.main()
