"""
Write Policy Guard — centralized filesystem write enforcement.

All filesystem writes in Ghost MUST go through this module. It normalizes
paths via realpath, checks containment within allowed directories, and
blocks traversal attacks with clear error messages.
"""

from pathlib import Path
from typing import Iterable, Union

PathLike = Union[str, Path]


class WritePolicyError(PermissionError):
    """Raised when a write is attempted outside allowed directories."""

    def __init__(self, target: Path, allowed: list[Path]):
        self.target = target
        self.allowed = allowed
        super().__init__(
            f"Write blocked: {target} is outside allowed directories.\n"
            f"Allowed directories:\n"
            + "\n".join(f"  \u2022 {p}" for p in allowed)
        )


class WriteGuard:
    """Enforces that all writes stay within an allowlist of directories.

    Args:
        allowed_dirs: One or more directories where writes are permitted.
            All are resolved to real, absolute paths at init time.
        create_parents: If True, auto-create parent dirs of targets (default).
        allow_project_root_files: If True, also allows files directly in the
            project root (ghost.toml, .env, .gitignore, etc.).
        project_root: Project root directory (used with allow_project_root_files).
    """

    def __init__(
        self,
        allowed_dirs: Union[PathLike, Iterable[PathLike]],
        create_parents: bool = True,
        allow_project_root_files: bool = False,
        project_root: Union[PathLike, None] = None,
    ):
        if isinstance(allowed_dirs, (str, Path)):
            allowed_dirs = [allowed_dirs]
        self._allowed = [Path(d).resolve() for d in allowed_dirs]
        self._create_parents = create_parents
        self._allow_project_root_files = allow_project_root_files
        self._project_root = Path(project_root).resolve() if project_root else None

    @property
    def allowed_dirs(self) -> list[Path]:
        return list(self._allowed)

    def check(self, target: PathLike) -> Path:
        """Resolve *target* and verify it is inside an allowed directory.

        Uses Path.resolve() to canonicalize the path (resolves .., symlinks)
        and checks containment via relative_to() to prevent ../ escape.

        Returns:
            The resolved absolute Path (safe to use for writes).

        Raises:
            WritePolicyError: if target escapes all allowed directories.
        """
        target = Path(target)
        resolved = target.resolve()

        if resolved in self._allowed:
            raise WritePolicyError(resolved, self._allowed)

        for base in self._allowed:
            try:
                resolved.relative_to(base)
                return resolved
            except ValueError:
                continue

        if self._allow_project_root_files and self._project_root:
            try:
                resolved.relative_to(self._project_root)
                if resolved.parent == self._project_root:
                    return resolved
            except ValueError:
                pass

        raise WritePolicyError(resolved, self._allowed)

    def write_text(
        self,
        target: PathLike,
        data: str,
        encoding: str = "utf-8",
    ) -> Path:
        """Write *data* to *target* after path validation."""
        resolved = self.check(target)
        if self._create_parents:
            resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(data, encoding=encoding)
        return resolved

    def write_bytes(self, target: PathLike, data: bytes) -> Path:
        """Write bytes to *target* after path validation."""
        resolved = self.check(target)
        if self._create_parents:
            resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_bytes(data)
        return resolved

    def mkdir(self, target: PathLike, parents: bool = True) -> Path:
        """Create a directory after path validation."""
        target = Path(target)
        resolved = target.resolve()

        for base in self._allowed:
            try:
                resolved.relative_to(base)
                resolved.mkdir(parents=parents, exist_ok=True)
                return resolved
            except ValueError:
                continue

        if self._allow_project_root_files and self._project_root:
            try:
                resolved.relative_to(self._project_root)
                resolved.mkdir(parents=parents, exist_ok=True)
                return resolved
            except ValueError:
                pass

        raise WritePolicyError(resolved, self._allowed)
