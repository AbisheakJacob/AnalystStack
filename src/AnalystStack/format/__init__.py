"""Formats and lints generated code so it comes out tidy and consistent.

Exposes two formatters:

* `PythonFormatter` — wraps [Ruff's](https://docs.astral.sh/ruff/formatter/)
  formatter plus an `ast`-based syntax check. Its methods operate on Python
  source code passed as strings and return strings.
* `SQLFormatter` — wraps [SQLFluff](https://sqlfluff.com/) and supports any
  SQLFluff dialect and templater, at a configurable `FormattingLevel` (from
  whitespace-only touch-ups up to a destructive structural rewrite via
  [sqlglot](https://sqlglot.com/)). Its methods read from and write to files
  on disk rather than strings.

Example:
    ```python
    from AnalystStack.format import FormattingLevel, PythonFormatter, SQLFormatter
    ```
"""

from .python import PythonFormatter
from .sql import FormattingLevel, SQLFormatter

# class CodeFormatManager:
#     """Facade for all code formatting and linting operations."""

#     def __init__(self, sql_config_path: Optional[str] = None):
#         # You can pass a path to a .sqlfluff file here
#         self.sql = SQLFormatter(config_path=sql_config_path)
#         self.python = PythonFormatter()


# # Instantiate the facade
# format_code = CodeFormatManager()

# __all__ = ["format_code", "CodeFormatManager"]

__all__ = ["SQLFormatter", "PythonFormatter", "FormattingLevel"]
