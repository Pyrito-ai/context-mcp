from __future__ import annotations

from pathlib import Path
import shutil
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from context_sync import SyncError, compare, sync  # noqa: E402


REVISION = "a" * 40


class SyncTests(unittest.TestCase):
    def create_target(self, directory: str) -> tuple[Path, Path]:
        repo = Path(directory) / "pyrito-mind"
        (repo / ".git").mkdir(parents=True)
        target = repo / "integrations" / "pyrito-context"
        (target / "skills" / "stale-skill").mkdir(parents=True)
        (target / "skills" / "stale-skill" / "SKILL.md").write_text("stale")
        (target / "templates").mkdir(parents=True)
        (target / "templates" / "obsolete.json").write_text("stale")
        (target / "README.md").write_text("Pyrito Mind-specific documentation\n")
        return repo, target

    def test_sync_is_bounded_idempotent_and_records_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            repo, target = self.create_target(directory)

            first = sync(ROOT, repo, REVISION)

            self.assertTrue(first)
            self.assertEqual(compare(ROOT, repo), [])
            self.assertEqual((target / "CONTEXT_MCP_REVISION").read_text(), REVISION + "\n")
            self.assertEqual(
                (target / "README.md").read_text(), "Pyrito Mind-specific documentation\n"
            )
            self.assertFalse((target / "skills" / "stale-skill").exists())
            self.assertFalse((target / "templates" / "obsolete.json").exists())
            self.assertEqual(sync(ROOT, repo, REVISION), [])

    def test_rejects_non_commit_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            repo, _ = self.create_target(directory)
            with self.assertRaises(SyncError):
                sync(ROOT, repo, "main")

    def test_rejects_symlinked_managed_target_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            repo, target = self.create_target(directory)
            external = Path(directory) / "external"
            external.mkdir()
            shutil.rmtree(target / "skills")
            (target / "skills").symlink_to(external, target_is_directory=True)

            with self.assertRaises(SyncError):
                sync(ROOT, repo, REVISION)

            self.assertEqual(list(external.iterdir()), [])
            self.assertFalse((target / "CONTEXT_MCP_REVISION").exists())


if __name__ == "__main__":
    unittest.main()
