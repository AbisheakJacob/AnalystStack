"""Path policy for every file the command-line interface reads or writes.

The CLI is the sanctioned way to touch data and files from inside an analyst workspace, so it
must not become a side door around the workspace's own protections. This module applies the
policy *before* any file is opened or parsed (parser errors can echo their input):

* no basename may look like an environment file (``.env``, ``.env.local``, ``prod.env``);
  only ``.env.example`` may be read, and nothing named like an env file may be written;
* when a workspace is detected (see `AnalystStack.workspace`), reads and writes must stay
  inside the workspace root;
* writes may only go under ``_state/``, ``global/`` or ``clients/``, never into a protected
  folder (``refs``, ``.claude``, ``scripts``, ``templates``, ``.git``) at any depth, and a
  path inside some ``tasks/NNNN_*`` folder must belong to the *active* task;
* outside any workspace only the environment-file rule applies, so the package stays usable
  as a plain library.

This is a guardrail against mistakes and prompt-driven misuse, not an operating-system
sandbox: code that imports the package directly is not subject to it.
"""

import os
import re
from pathlib import Path

from AnalystStack.exceptions.errors import PathPolicyError
from AnalystStack.workspace import active_task_dir, find_workspace_root

PROTECTED_SEGMENTS = frozenset({"refs", ".claude", "scripts", "templates", ".git"})
WRITABLE_TOP_LEVEL = frozenset({"_state", "global", "clients"})
_TASK_DIR = re.compile(r"^\d{4}_")


def _is_env_name(name: str) -> bool:
    lowered = name.lower()
    return lowered.startswith(".env") or lowered.endswith(".env")


def _is_env_example(name: str) -> bool:
    return name.lower() == ".env.example"


def _norm(path: Path) -> str:
    return os.path.normcase(str(path))


def _inside(path: Path, parent: Path) -> bool:
    child, base = _norm(path), _norm(parent)
    return child == base or child.startswith(base + os.sep)


def _resolve(path: str | Path) -> Path:
    # Symlinks are resolved for the parts that exist; not-yet-created files are accepted.
    return Path(path).expanduser().resolve()


def _governing_root(target: Path) -> Path | None:
    """Returns the workspace containing ``target``, else the one containing the cwd."""
    start = target if target.is_dir() else target.parent
    return find_workspace_root(start) or find_workspace_root()


def _check_name(target: Path, original: str | Path, *, write: bool) -> None:
    for name in {Path(original).name, target.name}:
        if _is_env_name(name) and (write or not _is_env_example(name)):
            verb = "write" if write else "read"
            raise PathPolicyError(f"Refusing to {verb} an environment file: {name!r}.")


def check_read(path: str | Path) -> Path:
    """Validates a path the CLI is about to read.

    Args:
        path: The path as supplied by the caller.

    Returns:
        The resolved path.

    Raises:
        AnalystStack.exceptions.errors.PathPolicyError: If the path names an environment file or
            lies outside the workspace governing it.
    """
    target = _resolve(path)
    _check_name(target, path, write=False)
    root = _governing_root(target)
    if root is not None and not _inside(target, root):
        raise PathPolicyError(f"Refusing to read outside the workspace: {target}")
    return target


def check_write(path: str | Path) -> Path:
    """Validates a path the CLI is about to write.

    Args:
        path: The path as supplied by the caller.

    Returns:
        The resolved path.

    Raises:
        AnalystStack.exceptions.errors.PathPolicyError: If the path names an environment file,
            lies outside the workspace, sits in a protected folder, is not under an allowed
            top-level folder, or belongs to a task that is not the active one.
    """
    target = _resolve(path)
    _check_name(target, path, write=True)
    root = _governing_root(target)
    if root is None:
        return target
    if not _inside(target, root):
        raise PathPolicyError(f"Refusing to write outside the workspace: {target}")
    parts = target.relative_to(root).parts
    if not parts or parts[0] not in WRITABLE_TOP_LEVEL:
        raise PathPolicyError(f"Writes are only allowed under {sorted(WRITABLE_TOP_LEVEL)}: {target}")
    hit = PROTECTED_SEGMENTS.intersection(parts)
    if hit:
        raise PathPolicyError(f"Refusing to write into protected folder {sorted(hit)[0]!r}: {target}")
    if "tasks" in parts:
        after = parts[parts.index("tasks") + 1 :]
        if after and _TASK_DIR.match(after[0]):
            active = active_task_dir(root)
            if active is None or not _inside(target, active):
                raise PathPolicyError(f"Path belongs to a task that is not the active task: {target}")
    return target
