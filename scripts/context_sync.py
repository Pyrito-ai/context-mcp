"""Safe, manifest-bounded synchronization helpers for Pyrito Mind."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import tempfile


REVISION_RE = re.compile(r"^[0-9a-f]{40}$")


class SyncError(RuntimeError):
    """A user-actionable synchronization error."""


@dataclass(frozen=True)
class SyncSpec:
    target_path: Path
    managed_files: tuple[Path, ...]
    managed_directories: tuple[Path, ...]
    revision_file: Path


def _safe_relative(value: object, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise SyncError(f"{label} must be a non-empty relative path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path == Path("."):
        raise SyncError(f"{label} must stay inside its declared root: {value}")
    return path


def load_spec(source_root: Path) -> SyncSpec:
    path = source_root / "sync" / "pyrito-mind.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SyncError(f"cannot read synchronization manifest: {path}") from exc
    if not isinstance(payload, dict):
        raise SyncError("synchronization manifest must contain an object")

    allowed = {"target_path", "managed_files", "managed_directories", "revision_file"}
    unknown = set(payload) - allowed
    if unknown:
        raise SyncError(f"unknown synchronization manifest fields: {', '.join(sorted(unknown))}")

    files = payload.get("managed_files")
    directories = payload.get("managed_directories")
    if not isinstance(files, list) or not files:
        raise SyncError("managed_files must be a non-empty list")
    if not isinstance(directories, list) or not directories:
        raise SyncError("managed_directories must be a non-empty list")

    spec = SyncSpec(
        target_path=_safe_relative(payload.get("target_path"), "target_path"),
        managed_files=tuple(_safe_relative(value, "managed_files entry") for value in files),
        managed_directories=tuple(
            _safe_relative(value, "managed_directories entry") for value in directories
        ),
        revision_file=_safe_relative(payload.get("revision_file"), "revision_file"),
    )
    overlaps = set(spec.managed_files) & set(spec.managed_directories)
    if overlaps:
        raise SyncError(f"managed file/directory overlap: {', '.join(map(str, sorted(overlaps)))}")
    return spec


def _regular_files(root: Path) -> set[Path]:
    if root.is_symlink():
        raise SyncError(f"symbolic links are not allowed in managed payloads: {root}")
    if not root.is_dir():
        raise SyncError(f"managed source directory is missing: {root}")
    files: set[Path] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise SyncError(f"symbolic links are not allowed in managed payloads: {path}")
        if path.is_file():
            files.add(path.relative_to(root))
    return files


def _reject_target_symlinks(target_root: Path, target: Path) -> None:
    try:
        relative = target.relative_to(target_root)
    except ValueError as exc:
        raise SyncError(f"managed target escapes integration root: {target}") from exc
    current = target_root
    if current.is_symlink():
        raise SyncError(f"symbolic links are not allowed in managed targets: {current}")
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise SyncError(f"symbolic links are not allowed in managed targets: {current}")


def managed_paths(source_root: Path, spec: SyncSpec) -> set[Path]:
    paths: set[Path] = set()
    for relative in spec.managed_files:
        source = source_root / relative
        if source.is_symlink() or not source.is_file():
            raise SyncError(f"managed source file is missing or not regular: {relative}")
        paths.add(relative)
    for directory in spec.managed_directories:
        for relative in _regular_files(source_root / directory):
            paths.add(directory / relative)
    return paths


def compare(source_root: Path, target_repo: Path) -> list[str]:
    source_root = source_root.resolve()
    target_repo = target_repo.resolve()
    spec = load_spec(source_root)
    target_root = target_repo / spec.target_path
    differences: list[str] = []

    for relative in sorted(managed_paths(source_root, spec)):
        source = source_root / relative
        target = target_root / relative
        if not target.is_file():
            differences.append(f"missing target: {relative}")
        elif source.read_bytes() != target.read_bytes():
            differences.append(f"content differs: {relative}")

    for directory in spec.managed_directories:
        source_files = _regular_files(source_root / directory)
        target_directory = target_root / directory
        target_files = _regular_files(target_directory) if target_directory.is_dir() else set()
        for relative in sorted(target_files - source_files):
            differences.append(f"stale target: {directory / relative}")
    return differences


def _copy_atomic(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(source.read_bytes())
    shutil.copymode(source, temporary)
    os.replace(temporary, target)


def _write_atomic(target: Path, contents: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=target.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(contents)
    temporary.chmod(0o644)
    os.replace(temporary, target)


def sync(source_root: Path, target_repo: Path, source_revision: str) -> list[str]:
    source_root = source_root.resolve()
    target_repo = target_repo.resolve()
    if not REVISION_RE.fullmatch(source_revision):
        raise SyncError("source revision must be a full lowercase 40-character Git SHA")
    if not (target_repo / ".git").exists():
        raise SyncError(f"target is not a Git checkout: {target_repo}")

    spec = load_spec(source_root)
    target_root = target_repo / spec.target_path
    if not target_root.is_dir():
        raise SyncError(f"target integration directory is missing: {target_root}")

    changed: list[str] = []
    expected = managed_paths(source_root, spec)
    for relative in expected:
        _reject_target_symlinks(target_root, target_root / relative)
    _reject_target_symlinks(target_root, target_root / spec.revision_file)
    target_files_by_directory: dict[Path, set[Path]] = {}
    for directory in spec.managed_directories:
        target_directory = target_root / directory
        _reject_target_symlinks(target_root, target_directory)
        target_files_by_directory[directory] = (
            _regular_files(target_directory) if target_directory.is_dir() else set()
        )

    for relative in sorted(expected):
        source = source_root / relative
        target = target_root / relative
        if not target.is_file() or source.read_bytes() != target.read_bytes():
            _copy_atomic(source, target)
            changed.append(f"updated {relative}")

    for directory in spec.managed_directories:
        source_files = _regular_files(source_root / directory)
        target_directory = target_root / directory
        target_files = target_files_by_directory[directory]
        for relative in sorted(target_files - source_files):
            stale = target_directory / relative
            stale.unlink()
            changed.append(f"removed {directory / relative}")
        if target_directory.is_dir():
            for candidate in sorted(target_directory.rglob("*"), reverse=True):
                if candidate.is_dir():
                    try:
                        candidate.rmdir()
                    except OSError:
                        pass

    revision_path = target_root / spec.revision_file
    revision_contents = source_revision + "\n"
    if not revision_path.is_file() or revision_path.read_text(encoding="utf-8") != revision_contents:
        _write_atomic(revision_path, revision_contents)
        changed.append(f"updated {spec.revision_file}")
    return changed
