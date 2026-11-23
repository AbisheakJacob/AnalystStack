"""``analyststack env``: report which environment keys are missing, by name only."""

import argparse
import sys

from AnalystStack.commands._common import EXIT_FAIL, default_scope, guarded
from AnalystStack.config.env_cascade import check_env


@guarded
def handle_env_check(args: argparse.Namespace) -> None:
    """Prints, per cascade level, the missing and extra key names. Never prints values."""
    scope = args.path or default_scope()
    problems = 0
    for level in check_env(scope):
        state = "present" if level["env_present"] else "MISSING"
        print(f"[{level['level']}] .env {state}; .env.example {'present' if level['example_present'] else 'MISSING'}")
        for key in level["missing"]:
            print(f"  missing key: {key}")
        for key in level["extra"]:
            print(f"  extra key:   {key}")
        problems += len(level["missing"]) + (0 if level["env_present"] else 1)
    if args.strict and problems:
        sys.exit(EXIT_FAIL)


def add_parser(subparsers) -> None:
    """Registers ``env``."""
    env = subparsers.add_parser("env", help="Inspect environment configuration (key names only).")
    sub = env.add_subparsers(dest="env_command", required=True)
    check = sub.add_parser("check", help="Compare each level's .env with .env.example, by key name.")
    check.add_argument("--path", default=None, help="Folder deciding which levels apply (default: active task or cwd).")
    check.add_argument("--strict", action="store_true", help="Exit non-zero if anything is missing.")
    check.set_defaults(func=handle_env_check)
