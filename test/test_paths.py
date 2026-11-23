"""Tests for workspace discovery and the CLI path policy."""

import pytest

from AnalystStack.exceptions.errors import PathPolicyError
from AnalystStack.paths import check_read, check_write
from AnalystStack.workspace import active_task_dir, find_workspace_root

TASK = "clients/acme/products/p1/tasks/0001_2026-11-23_demo"


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    (tmp_path / "global").mkdir()
    (tmp_path / "global" / "config.yaml").write_text("author: Test Author\n", encoding="utf-8")
    for sub in ("_state", "refs", ".claude", "scripts", "templates", "clients/acme/refs", TASK + "/work"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "_state" / "active_task").write_text(TASK, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_find_root_and_active_task(workspace):
    nested = workspace / TASK / "work"
    assert find_workspace_root(nested) == workspace.resolve()
    assert active_task_dir(workspace) == (workspace / TASK).resolve()


def test_active_task_pointer_outside_workspace_is_ignored(workspace):
    (workspace / "_state" / "active_task").write_text("../elsewhere", encoding="utf-8")
    assert active_task_dir(workspace) is None


@pytest.mark.parametrize("name", [".env", ".env.local", ".ENV", "prod.env", ".env.production"])
def test_env_files_are_never_readable(workspace, name):
    with pytest.raises(PathPolicyError):
        check_read(workspace / "global" / name)


def test_env_example_is_readable_but_not_writable(workspace):
    assert check_read(workspace / "global" / ".env.example")
    with pytest.raises(PathPolicyError):
        check_write(workspace / "global" / ".env.example")


def test_env_rule_applies_outside_a_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(PathPolicyError):
        check_read(tmp_path / ".env")
    assert check_write(tmp_path / "out.csv")


def test_reads_outside_the_workspace_are_refused(workspace, tmp_path_factory):
    other = tmp_path_factory.mktemp("other")
    (other / "f.csv").write_text("a\n1\n", encoding="utf-8")
    with pytest.raises(PathPolicyError):
        check_read(other / "f.csv")


@pytest.mark.parametrize("folder", ["refs", ".claude", "scripts", "templates", "clients/acme/refs"])
def test_protected_folders_cannot_be_written(workspace, folder):
    with pytest.raises(PathPolicyError):
        check_write(workspace / folder / "x.txt")


def test_writes_outside_allowed_top_level_are_refused(workspace):
    with pytest.raises(PathPolicyError):
        check_write(workspace / "CLAUDE.md")


def test_active_task_is_writable_other_tasks_are_not(workspace):
    assert check_write(workspace / TASK / "work" / "x.csv")
    other = workspace / "clients/acme/products/p1/tasks/0002_2026-11-23_other/work/x.csv"
    with pytest.raises(PathPolicyError):
        check_write(other)


def test_cd_elsewhere_does_not_escape_the_policy(workspace, tmp_path_factory, monkeypatch):
    elsewhere = tmp_path_factory.mktemp("elsewhere")
    monkeypatch.chdir(elsewhere)
    with pytest.raises(PathPolicyError):
        check_write(workspace / "refs" / "x.txt")
