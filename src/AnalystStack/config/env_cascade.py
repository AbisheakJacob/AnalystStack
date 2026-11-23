"""Layered ``.env`` loading for a global / client / product workspace.

Environment files live at three levels only, never inside a task:

    global/.env
    clients/<client>/.env
    clients/<client>/products/<product>/.env

`load_env_cascade` loads them in that order so a child level overrides its parent. A key's
*value* is never printed, logged, returned or put in an exception message; only key *names*
ever leave this module. `check_env` compares each level's ``.env`` against its committed
``.env.example`` and reports missing and extra key names.

The parser is deliberately small (``KEY=VALUE``, optional ``export`` prefix, single or double
quotes, ``#`` comments) so that no extra dependency is needed.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from AnalystStack.exceptions.errors import ConfigurationError
from AnalystStack.workspace import find_workspace_root

# Keys this module itself placed into ``os.environ``; those may be overridden by a later load.
_LOADED_BY_CASCADE: set[str] = set()


def _parse_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        key, sep, value = line.partition("=")
        key = key.strip()
        if not sep or not key or not key.replace("_", "").isalnum() or key[0].isdigit():
            continue
        value = value.strip()
        if value[:1] in ("'", '"') and value.endswith(value[:1]) and len(value) >= 2:
            value = value[1:-1]
        else:
            value = value.split(" #", 1)[0].rstrip()
        values[key] = value
    return values


def read_env_file(path: str | Path) -> dict[str, str]:
    """Parses one env file into a dict. Internal helper: callers must never print the values.

    Args:
        path: The env file.

    Returns:
        A mapping of key to value, empty if the file does not exist.
    """
    p = Path(path)
    return _parse_env(p.read_text(encoding="utf-8")) if p.is_file() else {}


def read_env_keys(path: str | Path) -> list[str]:
    """Returns only the key names of an env or env-example file, in file order.

    Args:
        path: The env file.

    Returns:
        The key names; empty if the file does not exist.
    """
    return list(read_env_file(path))


@dataclass
class EnvLevel:
    """One level of the cascade.

    Attributes:
        name: ``"global"``, ``"client"`` or ``"product"``.
        directory: The folder holding this level's ``.env`` and ``.env.example``.
    """

    name: str
    directory: Path
    env_file: Path = field(init=False)
    example_file: Path = field(init=False)

    def __post_init__(self) -> None:
        self.env_file = self.directory / ".env"
        self.example_file = self.directory / ".env.example"


def env_levels(path: str | Path, root: str | Path | None = None) -> list[EnvLevel]:
    """Works out which cascade levels apply to ``path``.

    Args:
        path: Any file or folder inside the workspace (a task, a product, a client folder).
        root: The workspace root; found by walking up from ``path`` when omitted.

    Returns:
        The levels from outermost to innermost: always global, then the client when ``path``
        is inside ``clients/<client>``, then the product when inside ``products/<product>``.

    Raises:
        AnalystStack.exceptions.errors.ConfigurationError: If ``path`` is not in a workspace.
    """
    target = Path(path).resolve()
    workspace = Path(root).resolve() if root is not None else find_workspace_root(target)
    if workspace is None:
        raise ConfigurationError(f"Not inside an analyst workspace: {target}")
    levels = [EnvLevel("global", workspace / "global")]
    try:
        parts = target.relative_to(workspace).parts
    except ValueError as exc:
        raise ConfigurationError(f"Path is outside the workspace: {target}") from exc
    if len(parts) >= 2 and parts[0] == "clients" and parts[1] != "_template":
        client_dir = workspace / "clients" / parts[1]
        levels.append(EnvLevel("client", client_dir))
        if len(parts) >= 4 and parts[2] == "products":
            levels.append(EnvLevel("product", client_dir / "products" / parts[3]))
    return levels


def load_env_cascade(
    path: str | Path,
    *,
    root: str | Path | None = None,
    environ: dict[str, str] | None = None,
) -> list[str]:
    """Loads the ``.env`` cascade that applies to ``path`` into the environment.

    Levels load global first, then client, then product, so each child overrides its parent.
    A variable that was already set in the real process environment by something other than
    this function is left alone, so deployment-injected values keep priority.

    Args:
        path: Any file or folder inside the workspace.
        root: The workspace root; found automatically when omitted.
        environ: The mapping to load into; defaults to ``os.environ``.

    Returns:
        The key names that were set, sorted. Values are never returned or logged.

    Raises:
        AnalystStack.exceptions.errors.ConfigurationError: If ``path`` is not in a workspace.
    """
    target_env = os.environ if environ is None else environ
    merged: dict[str, str] = {}
    for level in env_levels(path, root):
        merged.update(read_env_file(level.env_file))
    applied: list[str] = []
    for key, value in merged.items():
        if key in target_env and key not in _LOADED_BY_CASCADE:
            continue
        target_env[key] = value
        _LOADED_BY_CASCADE.add(key)
        applied.append(key)
    return sorted(applied)


def check_env(path: str | Path, root: str | Path | None = None) -> list[dict]:
    """Compares each level's ``.env`` with its ``.env.example``, by key name only.

    Args:
        path: Any file or folder inside the workspace.
        root: The workspace root; found automatically when omitted.

    Returns:
        One dict per level with ``level``, ``env_present``, ``example_present``, ``missing``
        (in the example but not in ``.env``) and ``extra`` (in ``.env`` but not in the
        example). Contains key names only.
    """
    report = []
    for level in env_levels(path, root):
        example_keys = read_env_keys(level.example_file)
        env_keys = read_env_keys(level.env_file)
        report.append(
            {
                "level": level.name,
                "directory": str(level.directory),
                "env_present": level.env_file.is_file(),
                "example_present": level.example_file.is_file(),
                "missing": [k for k in example_keys if k not in env_keys],
                "extra": [k for k in env_keys if k not in example_keys],
            }
        )
    return report
