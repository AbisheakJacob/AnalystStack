"""Saving every executed SQL statement into the active task's ``sql/`` folder.

Each distinct statement becomes ``sql/NN_slug.sql`` with a fixed header block::

    /*
    Author: <author>
    Date: YYYY/MM/DD
    Title: <title>
    Description: <description>
    */

followed by the statement itself. Run metadata (connection name, row count, timestamp, hash,
outcome) is appended to ``sql/_runs.jsonl`` instead of the header, so the header stays exactly
the four fields and the metadata can feed a provenance sheet. An identical statement (same
normalised text) reuses its existing file and only adds a run record.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from AnalystStack.exceptions.errors import ConfigurationError, ValidationError

SQL_DIR_NAME = "sql"
RUNS_FILE = "_runs.jsonl"
MIN_DESCRIPTION_LENGTH = 10
_HEADER_FIELD = re.compile(r"^(Author|Date|Title|Description):\s?(.*)$")


@dataclass(frozen=True)
class SavedQuery:
    """Where a statement was saved.

    Attributes:
        path: The ``.sql`` file.
        sha256: Hash of the normalised statement.
        reused: True if an identical statement had already been saved and its file was kept.
    """

    path: Path
    sha256: str
    reused: bool


def normalize_sql(sql: str) -> str:
    """Collapses whitespace and drops a trailing semicolon so equal statements hash equally."""
    return re.sub(r"\s+", " ", sql.strip()).rstrip(";").strip()


def sql_hash(sql: str) -> str:
    """Returns the SHA-256 of the normalised statement."""
    return hashlib.sha256(normalize_sql(sql).encode("utf-8")).hexdigest()


def _strip_header(text: str) -> str:
    """Returns the file content after its leading header block, if it has one."""
    stripped = text.lstrip()
    if stripped.startswith("/*") and "*/" in stripped:
        return stripped[stripped.index("*/") + 2 :]
    return text


def _slug(title: str, limit: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return (slug[:limit].strip("_")) or "query"


def build_header(author: str, title: str, description: str, date: datetime | None = None) -> str:
    """Builds the header block.

    Args:
        author: Who wrote the query.
        title: A one-line title.
        description: What the query does and why. Must not contain ``*/``.
        date: The date to print; defaults to now.

    Returns:
        The comment block, ending with a newline.

    Raises:
        AnalystStack.exceptions.errors.ValidationError: If a field is empty, the title spans
            several lines, the description is too short, or either contains ``*/``.
    """
    author, title, description = author.strip(), title.strip(), description.strip()
    if not author:
        raise ValidationError("Author must not be empty.")
    if not title or "\n" in title:
        raise ValidationError("Title must be a single non-empty line.")
    if len(description) < MIN_DESCRIPTION_LENGTH:
        raise ValidationError(f"Description must explain the query (at least {MIN_DESCRIPTION_LENGTH} characters).")
    for label, text in (("author", author), ("title", title), ("description", description)):
        if "*/" in text or "/*" in text:
            raise ValidationError(f"The {label} must not contain comment markers.")
    stamp = (date or datetime.now()).strftime("%Y/%m/%d")
    body = "\n".join(description.splitlines())
    return f"/*\nAuthor: {author}\nDate: {stamp}\nTitle: {title}\nDescription: {body}\n*/\n"


def parse_header(text: str) -> dict[str, str]:
    """Reads the header fields back from a saved file.

    Args:
        text: The file content.

    Returns:
        A dict with any of ``Author``, ``Date``, ``Title``, ``Description`` that were found;
        empty if the file does not start with a header block.
    """
    stripped = text.lstrip()
    if not stripped.startswith("/*") or "*/" not in stripped:
        return {}
    block = stripped[2 : stripped.index("*/")]
    fields: dict[str, str] = {}
    current = None
    for line in block.strip().splitlines():
        match = _HEADER_FIELD.match(line)
        if match:
            current = match.group(1)
            fields[current] = match.group(2).strip()
        elif current == "Description":
            fields[current] += "\n" + line.strip()
    return fields


def header_is_complete(text: str) -> bool:
    """True if the file starts with a header carrying all four non-empty fields."""
    fields = parse_header(text)
    return all(fields.get(k) for k in ("Author", "Date", "Title", "Description"))


def read_author(root: str | Path) -> str:
    """Reads ``author`` from ``<root>/global/config.yaml``.

    Raises:
        AnalystStack.exceptions.errors.ConfigurationError: If it is missing, so no author is
            ever invented.
    """
    import yaml

    config = Path(root) / "global" / "config.yaml"
    try:
        data = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigurationError(f"Cannot read {config}.") from exc
    author = data.get("author") if isinstance(data, dict) else None
    if not author or not str(author).strip():
        raise ConfigurationError("Set `author:` in global/config.yaml so saved SQL carries a header author.")
    return str(author).strip()


def _runs_path(task_dir: Path) -> Path:
    return task_dir / SQL_DIR_NAME / RUNS_FILE


def _read_runs(task_dir: Path) -> list[dict]:
    path = _runs_path(task_dir)
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def save_query(
    task_dir: str | Path,
    sql: str,
    title: str,
    description: str,
    *,
    author: str,
    date: datetime | None = None,
) -> SavedQuery:
    """Saves a statement under ``<task_dir>/sql/`` with its header.

    Args:
        task_dir: The task folder (or any folder that should receive a ``sql/`` subfolder).
        sql: The statement exactly as the analyst wrote it.
        title: A one-line title.
        description: What the query does and why.
        author: The header author.
        date: The header date; defaults to now.

    Returns:
        Where the statement lives, and whether an earlier identical save was reused.

    Raises:
        AnalystStack.exceptions.errors.ValidationError: If the header fields are invalid or the
            statement is empty.
    """
    if not sql.strip():
        raise ValidationError("Cannot save an empty statement.")
    folder = Path(task_dir) / SQL_DIR_NAME
    digest = sql_hash(sql)
    for existing in sorted(folder.glob("*.sql")):
        if sql_hash(_strip_header(existing.read_text(encoding="utf-8"))) == digest:
            return SavedQuery(existing, digest, reused=True)
    header = build_header(author, title, description, date)
    folder.mkdir(parents=True, exist_ok=True)
    taken = [int(m.group(1)) for p in folder.glob("*.sql") if (m := re.match(r"^(\d+)_", p.name))]
    number = (max(taken) if taken else 0) + 1
    path = folder / f"{number:02d}_{_slug(title)}.sql"
    path.write_text(header + sql.strip().rstrip(";") + ";\n", encoding="utf-8")
    return SavedQuery(path, digest, reused=False)


def record_run(
    task_dir: str | Path,
    saved: SavedQuery,
    *,
    connection: str | None,
    rows: int | None,
    ok: bool,
    seconds: float | None = None,
    note: str | None = None,
) -> None:
    """Appends one run record to ``sql/_runs.jsonl``.

    Args:
        task_dir: The task folder the statement was saved under.
        saved: The result of `save_query`.
        connection: The connection *name* (never a credential).
        rows: Rows returned, if known.
        ok: Whether the run succeeded.
        seconds: Wall-clock duration.
        note: A short note such as ``"row cap 100000 applied"``. Must not contain data values.
    """
    folder = Path(task_dir) / SQL_DIR_NAME
    folder.mkdir(parents=True, exist_ok=True)
    record = {
        "file": saved.path.name,
        "sha256": saved.sha256,
        "connection": connection,
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "rows": rows,
        "ok": ok,
        "seconds": None if seconds is None else round(seconds, 3),
        "note": note,
    }
    with _runs_path(Path(task_dir)).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def read_provenance(task_dir: str | Path) -> pd.DataFrame:
    """Builds a provenance table from a task's ``sql/`` folder.

    Args:
        task_dir: The task folder.

    Returns:
        One row per run with ``file``, ``title``, ``description``, ``connection``, ``run_at``,
        ``rows``, ``ok`` and ``sha256``. Empty (with those columns) if nothing was run.
    """
    columns = ["file", "title", "description", "connection", "run_at", "rows", "ok", "sha256"]
    folder = Path(task_dir) / SQL_DIR_NAME
    records = []
    for run in _read_runs(Path(task_dir)):
        path = folder / str(run.get("file", ""))
        header = parse_header(path.read_text(encoding="utf-8")) if path.is_file() else {}
        records.append(
            {
                "file": run.get("file"),
                "title": header.get("Title"),
                "description": header.get("Description"),
                "connection": run.get("connection"),
                "run_at": run.get("run_at"),
                "rows": run.get("rows"),
                "ok": run.get("ok"),
                "sha256": run.get("sha256"),
            }
        )
    return pd.DataFrame(records, columns=columns)
