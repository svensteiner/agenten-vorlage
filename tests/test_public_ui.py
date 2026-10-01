"""Static browser contract checks for the authenticated public gateway."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI_FILES = (
    ROOT / "cockpit" / "index.html",
    ROOT / "cockpit" / "chat.html",
    ROOT / "cockpit" / "assistants.html",
    ROOT / "cockpit" / "settings.html",
)


class PublicUiTests(unittest.TestCase):
    def test_mutations_bootstrap_csrf_without_breaking_local_server(self):
        for path in UI_FILES:
            source = path.read_text(encoding="utf-8")
            self.assertIn('fetch("/api/session"', source, path.name)
            self.assertIn('response.status === 404', source, path.name)
            self.assertIn('headers["X-CSRF-Token"] = csrfToken', source, path.name)
            self.assertIn('["POST", "PUT", "PATCH", "DELETE"]', source, path.name)

    def test_public_workspace_and_connection_labels_are_runtime_driven(self):
        for name in ("index.html", "chat.html"):
            source = (ROOT / "cockpit" / name).read_text(encoding="utf-8")
            self.assertIn("config.public_multiuser", source, name)
            self.assertIn("config.default_workspace", source, name)
            self.assertIn('state.publicMode ? "Verbunden" : "Lokal verbunden"', source, name)
        settings = (ROOT / "cockpit" / "settings.html").read_text(encoding="utf-8")
        self.assertIn('sourceLabels = { stored:', settings)
        self.assertIn('managed: "Serververwaltet"', settings)
        self.assertIn('status?.source === "managed"', settings)

    def test_public_chat_restricts_attachments_and_public_copy(self):
        chat = (ROOT / "cockpit" / "chat.html").read_text(encoding="utf-8")
        self.assertIn('state.publicMode && !TEXT_ATTACHMENT_EXTENSIONS.has(extension)', chat)
        self.assertIn('$("attachmentInput").accept = [...TEXT_ATTACHMENT_EXTENSIONS]', chat)
        self.assertIn("PDF, Office-Dateien und Bilder", chat)
        assistants = (ROOT / "cockpit" / "assistants.html").read_text(encoding="utf-8")
        self.assertIn('state.publicMode ? (agent.id || "ID nicht verfügbar")', assistants)
        self.assertIn("sichere IDs verwaltet", assistants)

    def test_csrf_token_is_memory_only(self):
        for path in UI_FILES:
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("localStorage.setItem", source, path.name)
            self.assertNotRegex(source, r"csrfToken[^;\n]{0,200}(?:localStorage|sessionStorage)", path.name)


if __name__ == "__main__":
    unittest.main()
