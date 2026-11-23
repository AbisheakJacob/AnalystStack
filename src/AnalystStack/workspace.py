"""Locating an analyst workspace and its active task.

A *workspace* is any directory tree whose root contains ``global/config.yaml``. The package
never needs to know anything else about the layout beyond this contract:

* the workspace root is the first directory, walking up from a starting path, that contains
  ``global/config.yaml``;
* the active task is named by the file ``_state/active_task`` under the root, whose single
  line is the task directory relative to the root (forward slashes).

An environment variable is deliberately not used for the active task, because a hook or a
child process cannot change the environment of later commands.
"""

from pathlib import Path

CONFIG_MARKER = Path("global") / "config.yaml"
ACTIVE_TASK_POINTER = Path("_state") / "active_task"


def find_workspace_root(start: str | Path | None = None) -> Path | None:
    """Walks up from ``start`` (default: the current directory) to find the workspace root.

    Args:
        start: A file or directory to start from.

    Returns:
        The resolved workspace root, or ``None`` if ``start`` is not inside a workspace.
    """
    here = Path(start) if start is not None else Path.cwd()
    here = here.resolve()
    for candidate in (here, *here.parents):
        if (candidate / CONFIG_MARKER).is_file():
            return candidate
    return None


def active_task_dir(root: str | Path) -> Path | None:
    """Reads the active-task pointer under ``root``.

    Args:
        root: The workspace root.

    Returns:
        The resolved active task directory, or ``None`` if no task is active, the pointer is
        empty, or it points outside the workspace or at something that is not a directory.
    """
    root = Path(root).resolve()
    pointer = root / ACTIVE_TASK_POINTER
    try:
        text = pointer.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not text:
        return None
    candidate = (root / text).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate if candidate.is_dir() else None
