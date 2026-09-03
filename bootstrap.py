#!/usr/bin/env python3
"""Install, migrate, and validate the Pyrito Context client integration."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Iterable
from urllib.parse import urlsplit


SERVER_NAME = "pyrito-context"
TOKEN_ENV = "PYRITO_CONTEXT_TOKEN"
LEGACY_HOOK_STATUS = "Preparing Pyrito context"
LEGACY_HOOK_DIR_NAME = ".pyrito-context"
LEGACY_HOOK_FILE_NAME = "session_start.py"
HOSTS = ("claude", "codex")
SKILL_NAMES = ("prepare-context", "capture-session", "invoke-agent")
EXPLICIT_ONLY_MARKER = "Do not invoke it automatically"


class BootstrapError(RuntimeError):
    """A user-actionable bootstrap error."""


def validate_endpoint(raw: str) -> str:
    endpoint = raw.strip().rstrip("/")
    parsed = urlsplit(endpoint)
    if parsed.scheme != "https" or not parsed.netloc:
        raise BootstrapError("Knowledge MCP endpoint must be an absolute HTTPS URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise BootstrapError("Knowledge MCP endpoint cannot contain credentials, a query, or a fragment")
    if parsed.path != "/knowledge-mcp":
        raise BootstrapError("Knowledge MCP endpoint path must be exactly /knowledge-mcp")
    return endpoint


def selected_hosts(value: str) -> tuple[str, ...]:
    return HOSTS if value == "both" else (value,)


def is_legacy_hook_handler(handler: Any) -> bool:
    if not isinstance(handler, dict) or handler.get("statusMessage") != LEGACY_HOOK_STATUS:
        return False
    command = handler.get("command")
    return (
        isinstance(command, str)
        and LEGACY_HOOK_DIR_NAME in command
        and LEGACY_HOOK_FILE_NAME in command
    )


def remove_legacy_startup_hook(config: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Remove only the startup handler installed by older bootstrap releases."""

    hooks = config.get("hooks")
    if hooks is None:
        return config, False
    if not isinstance(hooks, dict):
        raise BootstrapError("Existing hooks configuration is not an object")

    groups = hooks.get("SessionStart")
    if groups is None:
        return config, False
    if not isinstance(groups, list):
        raise BootstrapError("Existing SessionStart configuration is not a list")

    changed = False
    retained_groups: list[Any] = []
    for group in groups:
        if not isinstance(group, dict):
            retained_groups.append(group)
            continue
        handlers = group.get("hooks")
        if not isinstance(handlers, list):
            retained_groups.append(group)
            continue
        retained_handlers = [handler for handler in handlers if not is_legacy_hook_handler(handler)]
        if len(retained_handlers) == len(handlers):
            retained_groups.append(group)
            continue
        changed = True
        if retained_handlers:
            retained_group = dict(group)
            retained_group["hooks"] = retained_handlers
            retained_groups.append(retained_group)

    if not changed:
        return config, False
    if retained_groups:
        hooks["SessionStart"] = retained_groups
    else:
        hooks.pop("SessionStart", None)
    if not hooks:
        config.pop("hooks", None)
    return config, True


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise BootstrapError(f"Cannot read JSON configuration: {path}") from exc
    if not isinstance(value, dict):
        raise BootstrapError(f"JSON configuration must contain an object: {path}")
    return value


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    payload = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(payload)
        temporary_path = Path(handle.name)
    temporary_path.replace(path)


def mcp_add_command(host: str, endpoint: str) -> list[str]:
    if host == "claude":
        return [
            "claude",
            "mcp",
            "add",
            "--transport",
            "http",
            "--scope",
            "user",
            "--header",
            f"Authorization: Bearer ${{{TOKEN_ENV}}}",
            SERVER_NAME,
            endpoint,
        ]
    if host == "codex":
        return [
            "codex",
            "mcp",
            "add",
            SERVER_NAME,
            "--url",
            endpoint,
            "--bearer-token-env-var",
            TOKEN_ENV,
        ]
    raise BootstrapError(f"Unsupported host: {host}")


def mcp_remove_command(host: str) -> list[str]:
    if host == "claude":
        return ["claude", "mcp", "remove", "--scope", "user", SERVER_NAME]
    if host == "codex":
        return ["codex", "mcp", "remove", SERVER_NAME]
    raise BootstrapError(f"Unsupported host: {host}")


def mcp_get_command(host: str) -> list[str]:
    if host == "claude":
        return ["claude", "mcp", "get", SERVER_NAME]
    if host == "codex":
        return ["codex", "mcp", "get", SERVER_NAME, "--json"]
    raise BootstrapError(f"Unsupported host: {host}")


def codex_bearer_token_env(details: dict[str, Any]) -> Any:
    """Read both current nested and legacy flat Codex MCP JSON shapes."""

    transport = details.get("transport")
    if isinstance(transport, dict) and "bearer_token_env_var" in transport:
        return transport.get("bearer_token_env_var")
    return details.get("bearer_token_env_var")


def run_quiet(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, text=True, capture_output=True, check=check)
    except FileNotFoundError as exc:
        raise BootstrapError(f"Required host CLI is not installed: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise BootstrapError(f"Host command failed: {command[0]} {' '.join(command[1:3])}") from exc


def require_token() -> None:
    if not os.environ.get(TOKEN_ENV, "").strip():
        raise BootstrapError(f"Set {TOKEN_ENV} in the environment before continuing")


def config_path(host: str, user_root: Path) -> Path:
    if host == "claude":
        return user_root / ".claude" / "settings.json"
    if host == "codex":
        return user_root / ".codex" / "hooks.json"
    raise BootstrapError(f"Unsupported host: {host}")


def skill_target(host: str, name: str, user_root: Path) -> Path:
    if host == "claude":
        return user_root / ".claude" / "skills" / name
    if host == "codex":
        return user_root / ".codex" / "skills" / name
    raise BootstrapError(f"Unsupported host: {host}")


def skill_source(name: str) -> Path:
    source = Path(__file__).with_name("skills") / name
    if name not in SKILL_NAMES or not (source / "SKILL.md").is_file():
        raise BootstrapError(f"Bundled skill is missing or invalid: {name}")
    return source


def snapshot_file(path: Path) -> tuple[bool, bytes, int | None]:
    if not path.exists():
        return False, b"", None
    return True, path.read_bytes(), path.stat().st_mode & 0o7777


def restore_file(path: Path, snapshot: tuple[bool, bytes, int | None]) -> None:
    existed, content, mode = snapshot
    if not existed:
        if path.exists():
            path.unlink()
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary_path = Path(handle.name)
    if mode is not None:
        temporary_path.chmod(mode)
    temporary_path.replace(path)


def rollback_registrations(hosts: Iterable[str]) -> list[str]:
    failed: list[str] = []
    for host in reversed(tuple(hosts)):
        try:
            result = run_quiet(mcp_remove_command(host), check=False)
        except BootstrapError:
            failed.append(host)
            continue
        if result.returncode != 0:
            try:
                still_present = run_quiet(mcp_get_command(host), check=False).returncode == 0
            except BootstrapError:
                still_present = True
            if still_present:
                failed.append(host)
    return failed


def install(args: argparse.Namespace) -> None:
    endpoint = validate_endpoint(args.endpoint)
    require_token()
    hosts = selected_hosts(args.host)
    user_root = Path.home()
    pending_skills: list[tuple[Path, Path]] = []

    for host in hosts:
        if shutil.which(host) is None:
            raise BootstrapError(f"Required host CLI is not installed: {host}")
        for name in SKILL_NAMES:
            source = skill_source(name)
            skill = skill_target(host, name, user_root)
            if skill.exists():
                raise BootstrapError(
                    f"Skill already exists in {host}: {skill}; remove or preserve it explicitly first"
                )
            pending_skills.append((source, skill))

        present = run_quiet(mcp_get_command(host), check=False).returncode == 0
        if present:
            raise BootstrapError(
                f"{SERVER_NAME} already exists in {host}; validate or remove it explicitly first"
            )

    added_hosts: list[str] = []
    unverified_failed_host: str | None = None
    created_skill_dirs: list[Path] = []

    try:
        for host in hosts:
            try:
                run_quiet(mcp_add_command(host, endpoint))
            except BootstrapError:
                # Some CLIs can persist a registration before returning an error.
                # Only roll it back when a post-failure lookup proves it now exists.
                try:
                    if run_quiet(mcp_get_command(host), check=False).returncode == 0:
                        added_hosts.append(host)
                except BootstrapError:
                    unverified_failed_host = host
                raise
            added_hosts.append(host)
    except BootstrapError as exc:
        failed = rollback_registrations(added_hosts)
        details: list[str] = []
        if failed:
            details.append(f"rollback failed for: {', '.join(failed)}")
        if unverified_failed_host:
            details.append(f"could not verify partial state for: {unverified_failed_host}")
        detail = f"; {'; '.join(details)}" if details else ""
        raise BootstrapError(f"MCP registration failed and new registrations were rolled back{detail}") from exc

    try:
        for source, target in pending_skills:
            created_skill_dirs.append(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, target)
    except OSError as exc:
        restore_failures: list[str] = []
        for target in reversed(created_skill_dirs):
            try:
                if target.exists():
                    shutil.rmtree(target)
            except OSError:
                restore_failures.append(str(target))
        registration_failures = rollback_registrations(added_hosts)
        details: list[str] = []
        if restore_failures:
            details.append(f"file restore failed for: {', '.join(restore_failures)}")
        if registration_failures:
            details.append(f"MCP rollback failed for: {', '.join(registration_failures)}")
        suffix = f"; {'; '.join(details)}" if details else ""
        raise BootstrapError(f"Context installation failed and new state was rolled back{suffix}") from exc

    for host in hosts:
        print(f"Configured {host} (token remains in {TOKEN_ENV})")


def find_legacy_hook(config: dict[str, Any]) -> dict[str, Any] | None:
    groups = config.get("hooks", {}).get("SessionStart", [])
    if not isinstance(groups, list):
        return None
    for group in groups:
        if not isinstance(group, dict):
            continue
        for handler in group.get("hooks", []):
            if is_legacy_hook_handler(handler):
                return group
    return None


def invocation_only(args: argparse.Namespace) -> None:
    """Remove legacy automatic recall and install missing explicit skills."""

    hosts = selected_hosts(args.host)
    user_root = Path.home()
    installed_hook = user_root / LEGACY_HOOK_DIR_NAME / LEGACY_HOOK_FILE_NAME
    pending_configs: dict[str, tuple[Path, dict[str, Any]]] = {}
    pending_skills: list[tuple[Path, Path]] = []

    for host in hosts:
        target = config_path(host, user_root)
        config, changed = remove_legacy_startup_hook(load_json_object(target))
        if changed:
            pending_configs[host] = (target, config)
        for name in SKILL_NAMES:
            source = skill_source(name)
            skill = skill_target(host, name, user_root)
            if skill.exists():
                if not (skill / "SKILL.md").is_file():
                    raise BootstrapError(f"Existing {host} skill is invalid: {skill}")
                if name == "prepare-context" and EXPLICIT_ONLY_MARKER not in (
                    skill / "SKILL.md"
                ).read_text(encoding="utf-8"):
                    raise BootstrapError(
                        f"Existing {host} prepare-context skill is not invocation-only; "
                        "preserve or remove it explicitly before retrying"
                    )
                continue
            pending_skills.append((source, skill))

    config_targets = [target for target, _ in pending_configs.values()]
    changed_paths = [
        installed_hook,
        *config_targets,
        *(target.with_suffix(target.suffix + ".bak") for target in config_targets),
    ]
    snapshots = {path: snapshot_file(path) for path in changed_paths}
    created_skill_dirs: list[Path] = []

    try:
        for source, target in pending_skills:
            created_skill_dirs.append(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, target)
        for target, config in pending_configs.values():
            write_json_atomic(target, config)

        still_referenced = any(
            find_legacy_hook(load_json_object(config_path(host, user_root))) is not None
            for host in HOSTS
        )
        if installed_hook.exists() and not still_referenced:
            installed_hook.unlink()
            try:
                installed_hook.parent.rmdir()
            except OSError:
                pass
    except (BootstrapError, OSError) as exc:
        restore_failures: list[str] = []
        for target in reversed(created_skill_dirs):
            try:
                if target.exists():
                    shutil.rmtree(target)
            except OSError:
                restore_failures.append(str(target))
        for path in reversed(changed_paths):
            try:
                restore_file(path, snapshots[path])
            except OSError:
                restore_failures.append(str(path))
        suffix = f"; restore failed for: {', '.join(restore_failures)}" if restore_failures else ""
        raise BootstrapError(f"Invocation-only migration failed and prior state was restored{suffix}") from exc

    for host in hosts:
        action = "Removed legacy startup hook from" if host in pending_configs else "No legacy startup hook found in"
        print(f"{action} {host}; context is now explicit-skill only")


def validate(args: argparse.Namespace) -> None:
    endpoint = validate_endpoint(args.endpoint)
    require_token()
    user_root = Path.home()

    for host in selected_hosts(args.host):
        for name in SKILL_NAMES:
            target = skill_target(host, name, user_root)
            if not (target / "SKILL.md").is_file():
                raise BootstrapError(f"{host} skill is missing: {name}")
            if name == "prepare-context" and EXPLICIT_ONLY_MARKER not in (
                target / "SKILL.md"
            ).read_text(encoding="utf-8"):
                raise BootstrapError(f"{host} prepare-context skill is not invocation-only")
        if find_legacy_hook(load_json_object(config_path(host, user_root))) is not None:
            raise BootstrapError(
                f"{host} still has the legacy automatic startup hook; run invocation-only first"
            )
        result = run_quiet(mcp_get_command(host))
        if endpoint not in result.stdout:
            raise BootstrapError(f"{host} MCP registration does not use the expected endpoint")
        if host == "codex":
            try:
                details = json.loads(result.stdout)
            except json.JSONDecodeError as exc:
                raise BootstrapError("Codex returned invalid MCP configuration JSON") from exc
            if codex_bearer_token_env(details) != TOKEN_ENV:
                raise BootstrapError(f"Codex MCP registration must use {TOKEN_ENV}")
        elif TOKEN_ENV not in result.stdout:
            raise BootstrapError(f"Claude MCP registration must reference {TOKEN_ENV}")
        print(f"Validated {host}")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    for name, handler in (
        ("install", install),
        ("invocation-only", invocation_only),
        ("validate", validate),
    ):
        command = commands.add_parser(name)
        command.add_argument("--host", choices=(*HOSTS, "both"), default="both")
        if name != "invocation-only":
            command.add_argument("--endpoint", required=True)
        command.set_defaults(handler=handler)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        args.handler(args)
    except BootstrapError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
