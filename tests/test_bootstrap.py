from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_bootstrap():
    spec = importlib.util.spec_from_file_location("pyrito_context_bootstrap", ROOT / "bootstrap.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bootstrap = load_bootstrap()


class EndpointTests(unittest.TestCase):
    def test_accepts_exact_https_endpoint(self):
        self.assertEqual(
            bootstrap.validate_endpoint("https://mind.example.com/knowledge-mcp/"),
            "https://mind.example.com/knowledge-mcp",
        )

    def test_rejects_http_wrong_path_and_embedded_credentials(self):
        invalid = (
            "http://mind.example.com/knowledge-mcp",
            "https://mind.example.com/mcp",
            "https://token@mind.example.com/knowledge-mcp",
            "https://mind.example.com/knowledge-mcp?token=secret",
        )
        for endpoint in invalid:
            with self.subTest(endpoint=endpoint), self.assertRaises(bootstrap.BootstrapError):
                bootstrap.validate_endpoint(endpoint)


class ConfigurationTests(unittest.TestCase):
    def test_templates_are_secret_free_and_context_is_explicit_only(self):
        claude_mcp = json.loads((ROOT / "templates" / "claude.mcp.json").read_text())
        codex_config = (ROOT / "templates" / "codex.config.toml").read_text()
        prepare_context = (ROOT / "skills" / "prepare-context" / "SKILL.md").read_text()

        self.assertEqual(
            claude_mcp["mcpServers"]["pyrito-context"]["headers"]["Authorization"],
            "Bearer ${PYRITO_CONTEXT_TOKEN}",
        )
        self.assertFalse((ROOT / "templates" / "claude.hooks.json").exists())
        self.assertFalse((ROOT / "templates" / "codex.hooks.json").exists())
        self.assertIn('bearer_token_env_var = "PYRITO_CONTEXT_TOKEN"', codex_config)
        self.assertIn('url = "<PYRITO_KNOWLEDGE_MCP_URL>"', codex_config)
        self.assertIn('"capture_session"', codex_config)
        self.assertIn('"prepare_agent"', codex_config)
        self.assertNotIn("sk-mem", codex_config)
        self.assertIn("invoke-agent", bootstrap.SKILL_NAMES)
        self.assertIn("required = false", codex_config)
        self.assertIn("only when the user explicitly", prepare_context)
        self.assertIn("Do not invoke it automatically", prepare_context)

        for name in bootstrap.SKILL_NAMES:
            self.assertTrue((bootstrap.skill_source(name) / "SKILL.md").is_file())

    def test_remove_legacy_hook_preserves_other_handlers_and_is_idempotent(self):
        original = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "startup",
                        "hooks": [
                            {"type": "command", "command": "other"},
                            {
                                "type": "command",
                                "command": "python ~/.pyrito-context/session_start.py",
                                "statusMessage": bootstrap.LEGACY_HOOK_STATUS,
                            },
                        ],
                    }
                ]
            }
        }
        first, first_changed = bootstrap.remove_legacy_startup_hook(original)
        second, second_changed = bootstrap.remove_legacy_startup_hook(first)
        self.assertTrue(first_changed)
        self.assertFalse(second_changed)
        self.assertEqual(
            second["hooks"]["SessionStart"][0]["hooks"],
            [{"type": "command", "command": "other"}],
        )
        self.assertIsNone(bootstrap.find_legacy_hook(second))

    def test_mcp_commands_reference_environment_not_secret(self):
        endpoint = "https://mind.example.com/knowledge-mcp"
        claude = bootstrap.mcp_add_command("claude", endpoint)
        codex = bootstrap.mcp_add_command("codex", endpoint)
        self.assertIn("Authorization: Bearer ${PYRITO_CONTEXT_TOKEN}", claude)
        self.assertIn("--bearer-token-env-var", codex)
        self.assertIn("PYRITO_CONTEXT_TOKEN", codex)

    def test_codex_bearer_token_supports_current_and_legacy_json_shapes(self):
        self.assertEqual(
            bootstrap.codex_bearer_token_env({
                "transport": {"bearer_token_env_var": "PYRITO_CONTEXT_TOKEN"}
            }),
            "PYRITO_CONTEXT_TOKEN",
        )
        self.assertEqual(
            bootstrap.codex_bearer_token_env({
                "bearer_token_env_var": "PYRITO_CONTEXT_TOKEN"
            }),
            "PYRITO_CONTEXT_TOKEN",
        )

    def test_skill_targets_are_host_native(self):
        root = Path("/tmp/test-user")
        self.assertEqual(
            bootstrap.skill_target("claude", "prepare-context", root),
            root / ".claude" / "skills" / "prepare-context",
        )
        self.assertEqual(
            bootstrap.skill_target("codex", "capture-session", root),
            root / ".codex" / "skills" / "capture-session",
        )

    def test_install_copies_skills_without_modifying_hooks(self):
        with tempfile.TemporaryDirectory() as directory:
            user_root = Path(directory)
            claude_config = user_root / ".claude" / "settings.json"
            claude_config.parent.mkdir(parents=True)
            claude_config.write_text(
                json.dumps({
                    "hooks": {
                        "SessionStart": [{
                            "matcher": "resume",
                            "hooks": [{"type": "command", "command": "other"}],
                        }]
                    }
                })
            )

            def fake_run(command, *, check=True):
                if command[1:3] == ["mcp", "get"]:
                    return subprocess.CompletedProcess(command, 1, "", "")
                return subprocess.CompletedProcess(command, 0, "", "")

            args = bootstrap.argparse.Namespace(
                endpoint="https://mind.example.com/knowledge-mcp", host="both"
            )
            with (
                mock.patch.object(bootstrap.Path, "home", return_value=user_root),
                mock.patch.object(bootstrap.shutil, "which", return_value="/bin/host"),
                mock.patch.object(bootstrap, "run_quiet", side_effect=fake_run),
                mock.patch.dict(bootstrap.os.environ, {bootstrap.TOKEN_ENV: "test-only"}),
            ):
                bootstrap.install(args)

            for host in ("claude", "codex"):
                for name in bootstrap.SKILL_NAMES:
                    target = bootstrap.skill_target(host, name, user_root)
                    self.assertTrue((target / "SKILL.md").is_file())
            installed = json.loads(claude_config.read_text())
            groups = installed["hooks"]["SessionStart"]
            self.assertEqual({group["matcher"] for group in groups}, {"resume"})
            self.assertFalse(claude_config.with_suffix(".json.bak").exists())

    def test_later_mcp_failure_rolls_back_only_registration_added_by_run(self):
        with tempfile.TemporaryDirectory() as directory:
            user_root = Path(directory)
            calls: list[list[str]] = []
            add_count = 0

            def fake_run(command, *, check=True):
                nonlocal add_count
                calls.append(command)
                if command[1:3] == ["mcp", "get"]:
                    if command[0] == "codex" and add_count == 2:
                        return subprocess.CompletedProcess(command, 0, "", "")
                    return subprocess.CompletedProcess(command, 1, "", "")
                if command[1:3] == ["mcp", "add"]:
                    add_count += 1
                    if add_count == 2:
                        raise bootstrap.BootstrapError("second add failed")
                return subprocess.CompletedProcess(command, 0, "", "")

            args = bootstrap.argparse.Namespace(
                endpoint="https://mind.example.com/knowledge-mcp", host="both"
            )
            with (
                mock.patch.object(bootstrap.Path, "home", return_value=user_root),
                mock.patch.object(bootstrap.shutil, "which", return_value="/bin/host"),
                mock.patch.object(bootstrap, "run_quiet", side_effect=fake_run),
                mock.patch.dict(bootstrap.os.environ, {bootstrap.TOKEN_ENV: "test-only"}),
                self.assertRaises(bootstrap.BootstrapError),
            ):
                bootstrap.install(args)

            remove_calls = [call for call in calls if call[1:3] == ["mcp", "remove"]]
            self.assertEqual(
                remove_calls,
                [
                    ["codex", "mcp", "remove", "pyrito-context"],
                    ["claude", "mcp", "remove", "--scope", "user", "pyrito-context"],
                ],
            )
            self.assertFalse((user_root / ".claude" / "settings.json").exists())
            self.assertFalse((user_root / ".codex" / "hooks.json").exists())

    def test_skill_copy_failure_removes_new_skills_and_registrations(self):
        with tempfile.TemporaryDirectory() as directory:
            user_root = Path(directory)
            calls: list[list[str]] = []

            def fake_run(command, *, check=True):
                calls.append(command)
                if command[1:3] == ["mcp", "get"]:
                    return subprocess.CompletedProcess(command, 1, "", "")
                return subprocess.CompletedProcess(command, 0, "", "")

            args = bootstrap.argparse.Namespace(
                endpoint="https://mind.example.com/knowledge-mcp", host="both"
            )
            with (
                mock.patch.object(bootstrap.Path, "home", return_value=user_root),
                mock.patch.object(bootstrap.shutil, "which", return_value="/bin/host"),
                mock.patch.object(bootstrap, "run_quiet", side_effect=fake_run),
                mock.patch.object(
                    bootstrap.shutil,
                    "copytree",
                    side_effect=[None, OSError("copy failed")],
                ),
                mock.patch.dict(bootstrap.os.environ, {bootstrap.TOKEN_ENV: "test-only"}),
                self.assertRaises(bootstrap.BootstrapError),
            ):
                bootstrap.install(args)

            for host in ("claude", "codex"):
                for name in bootstrap.SKILL_NAMES:
                    self.assertFalse(bootstrap.skill_target(host, name, user_root).exists())
            remove_hosts = [call[0] for call in calls if call[1:3] == ["mcp", "remove"]]
            self.assertEqual(remove_hosts, ["codex", "claude"])

    def test_invocation_only_migrates_legacy_hooks_and_installs_missing_skills(self):
        with tempfile.TemporaryDirectory() as directory:
            user_root = Path(directory)
            installed_hook = user_root / ".pyrito-context" / "session_start.py"
            installed_hook.parent.mkdir(parents=True)
            installed_hook.write_text("legacy")

            for host in bootstrap.HOSTS:
                target = bootstrap.config_path(host, user_root)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps({
                    "hooks": {
                        "SessionStart": [
                            {
                                "matcher": "startup",
                                "hooks": [{
                                    "type": "command",
                                    "command": "python ~/.pyrito-context/session_start.py",
                                    "statusMessage": bootstrap.LEGACY_HOOK_STATUS,
                                }],
                            },
                            {
                                "matcher": "resume",
                                "hooks": [{"type": "command", "command": "other"}],
                            },
                        ]
                    }
                }))

            args = bootstrap.argparse.Namespace(host="both")
            with mock.patch.object(bootstrap.Path, "home", return_value=user_root):
                bootstrap.invocation_only(args)

            for host in bootstrap.HOSTS:
                config = bootstrap.load_json_object(bootstrap.config_path(host, user_root))
                self.assertIsNone(bootstrap.find_legacy_hook(config))
                self.assertEqual(config["hooks"]["SessionStart"][0]["matcher"], "resume")
                for name in bootstrap.SKILL_NAMES:
                    skill = bootstrap.skill_target(host, name, user_root) / "SKILL.md"
                    self.assertTrue(skill.is_file())
            self.assertFalse(installed_hook.exists())

    def test_invocation_only_preserves_hook_file_while_other_host_references_it(self):
        with tempfile.TemporaryDirectory() as directory:
            user_root = Path(directory)
            installed_hook = user_root / ".pyrito-context" / "session_start.py"
            installed_hook.parent.mkdir(parents=True)
            installed_hook.write_text("legacy")
            claude_config = bootstrap.config_path("claude", user_root)
            claude_config.parent.mkdir(parents=True)
            claude_config.write_text(json.dumps({
                "hooks": {"SessionStart": [{
                    "matcher": "startup",
                    "hooks": [{
                        "command": "python ~/.pyrito-context/session_start.py",
                        "statusMessage": bootstrap.LEGACY_HOOK_STATUS,
                    }],
                }]}
            }))

            args = bootstrap.argparse.Namespace(host="codex")
            with mock.patch.object(bootstrap.Path, "home", return_value=user_root):
                bootstrap.invocation_only(args)

            self.assertTrue(installed_hook.exists())


if __name__ == "__main__":
    unittest.main()
