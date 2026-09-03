from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SyncWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.workflow = (ROOT / ".github" / "workflows" / "sync-pyrito-mind.yml").read_text(
            encoding="utf-8"
        )

    def test_uses_narrow_github_app_credentials(self):
        self.assertIn("PYRITO_SYNC_APP_ID", self.workflow)
        self.assertIn("PYRITO_SYNC_PRIVATE_KEY", self.workflow)
        self.assertIn("repositories: pyrito-mind", self.workflow)
        self.assertNotIn("personal access token", self.workflow.lower())

    def test_opens_review_branch_without_automatic_merge(self):
        self.assertIn("refs/heads/automation/context-mcp-sync", self.workflow)
        self.assertIn("gh pr create", self.workflow)
        self.assertNotIn("gh pr merge", self.workflow)
        self.assertNotIn("pull_request_target", self.workflow)
        self.assertNotIn("HEAD:refs/heads/main", self.workflow)

    def test_third_party_actions_are_commit_pinned(self):
        for line in self.workflow.splitlines():
            stripped = line.strip()
            if stripped.startswith("uses:"):
                revision = stripped.rsplit("@", 1)[-1]
                self.assertRegex(revision, r"^[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
