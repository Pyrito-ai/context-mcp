from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://proxy.memory.pyrito.com/knowledge-mcp"
TOKEN_ENV = "PYRITO_CONTEXT_TOKEN"
EXPECTED_TOOLS = {
    "prepare_context",
    "search_knowledge",
    "read_knowledge_page",
    "prepare_agent",
    "capture_session",
}


class PluginPackageTests(unittest.TestCase):
    def load_json(self, relative: str):
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))

    def test_host_manifests_share_identity_and_version(self):
        codex = self.load_json(".codex-plugin/plugin.json")
        claude = self.load_json(".claude-plugin/plugin.json")
        self.assertEqual(codex["name"], "context-mcp")
        self.assertEqual(claude["name"], "context-mcp")
        self.assertEqual(codex["version"], claude["version"])

    def test_codex_uses_environment_bearer_and_bounded_tools(self):
        server = self.load_json(".codex-plugin/plugin.json")["mcpServers"]["pyrito-context"]
        self.assertEqual(server["url"], ENDPOINT)
        self.assertEqual(server["bearer_token_env_var"], TOKEN_ENV)
        self.assertEqual(set(server["enabled_tools"]), EXPECTED_TOOLS)
        self.assertFalse(server["required"])

    def test_claude_uses_environment_bearer(self):
        manifest = self.load_json(".claude-plugin/plugin.json")
        self.assertEqual(manifest["mcpServers"], "./.claude-plugin/mcp.json")
        server = self.load_json(".claude-plugin/mcp.json")["mcpServers"]["pyrito-context"]
        self.assertEqual(server["url"], ENDPOINT)
        self.assertEqual(server["headers"]["Authorization"], f"Bearer ${{{TOKEN_ENV}}}")

    def test_distribution_is_invocation_only(self):
        self.assertFalse((ROOT / "hooks").exists())
        self.assertFalse((ROOT / "session_start.py").exists())
        prepare = (ROOT / "skills" / "prepare-context" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        capture = (ROOT / "skills" / "capture-session" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Do not invoke it automatically", prepare)
        self.assertIn("Do not capture anything unless the user explicitly asks", capture)

    def test_marketplace_points_to_repository_plugin_root(self):
        marketplace = self.load_json(".claude-plugin/marketplace.json")
        self.assertEqual(marketplace["name"], "context-mcp")
        self.assertEqual(marketplace["plugins"][0]["name"], "context-mcp")
        self.assertEqual(marketplace["plugins"][0]["source"], "./")

    def test_teammate_setup_is_public_agent_guided_and_secret_safe(self):
        teammate = (ROOT / "docs" / "TEAMMATE-SETUP.md").read_text(encoding="utf-8")
        runbook = (ROOT / "docs" / "AGENT-INSTALL.md").read_text(encoding="utf-8")
        combined = f"{teammate}\n{runbook}".lower()

        self.assertIn("https://github.com/pyrito-ai/context-mcp", combined)
        self.assertIn("does not require a github account", combined)
        self.assertIn("do not ask me to paste", combined)
        self.assertIn("hidden local input", combined)
        self.assertIn("restart", teammate.lower())
        self.assertIn("verification prompt", teammate.lower())
        self.assertNotIn("pyrito-ai/pyrito-mind.git", combined)
        self.assertNotIn("gh auth login", combined)


if __name__ == "__main__":
    unittest.main()
