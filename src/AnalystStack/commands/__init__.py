"""Command modules behind the ``analyststack`` console script.

Each module exposes ``add_parser(subparsers)`` and registers one command group:

* ``env``: report missing environment keys by name (`AnalystStack.commands.env_cmd`);
* ``db``: read-only database access, every statement saved to the task
  (`AnalystStack.commands.db_cmd`);
* ``io``: render Jinja templates, convert and preview files (`AnalystStack.commands.io_cmd`);
* ``data``: tidy, untidy, compare, summarise and validate files
  (`AnalystStack.commands.data_cmd`);
* ``report`` and ``excel``: markdown and branded Excel deliverables
  (`AnalystStack.commands.report_cmd`).

``format`` lives in `AnalystStack.cli` itself. Exit codes: ``0`` success, ``1`` an expected
failure (bad input, failed check), ``2`` blocked by the path policy or the read-only guard.
"""

from AnalystStack.commands import data_cmd, db_cmd, env_cmd, io_cmd, report_cmd

GROUPS = (env_cmd, db_cmd, io_cmd, data_cmd, report_cmd)


def register_all(subparsers) -> None:
    """Registers every command group on ``subparsers``."""
    for group in GROUPS:
        group.add_parser(subparsers)
