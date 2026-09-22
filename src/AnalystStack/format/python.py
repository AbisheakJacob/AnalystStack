import ast
import subprocess

from AnalystStack.utils.logging import get_logger

logger = get_logger(__name__)

try:
    from ruff.__main__ import find_ruff_bin

    _RUFF_BIN = find_ruff_bin()
except ImportError:
    # Falls back to whatever `ruff` is on PATH if the `ruff` package (which
    # bundles its own binary) isn't importable, e.g. a system-wide install.
    _RUFF_BIN = "ruff"


class PythonFormatter:
    """Handles Python linting and formatting using Ruff and AST.

    Wraps [Ruff's](https://docs.astral.sh/ruff/formatter/) formatter (invoked
    as a subprocess, since Ruff ships no in-process formatting API) plus the
    standard library `ast` module for a lightweight syntax check. Unlike
    `SQLFormatter`, which reads from and writes to files on disk,
    `PythonFormatter`'s methods operate on Python source code passed directly
    as strings and return strings — callers are responsible for
    reading/writing any files themselves.

    Example:
        ```python
        from AnalystStack.format import PythonFormatter

        fmt = PythonFormatter(line_length=100)
        ```
    """

    def __init__(self, line_length: int = 100):
        """Initializes the formatter.

        Args:
            line_length: Maximum line length Ruff should target when
                formatting code with `format_code`.
        """
        self.line_length = line_length

    def view_errors(self, code_string: str) -> list[str]:
        """
        Checks for fundamental Python syntax errors without executing the code.

        Parses ``code_string`` with `ast.parse` — a lightweight check that never
        executes the code — and reports any `SyntaxError` encountered.

        Args:
            code_string: The Python source code to check, as a string.

        Returns:
            A list of error messages (empty if the code is syntactically clean).

        Example:
            ```python
            fmt = PythonFormatter(line_length=100)
            errors = fmt.view_errors("def f(:\\n  pass")  # ["SyntaxError on line 1, ..."]
            ```
        """
        errors = []
        try:
            ast.parse(code_string)
            logger.info("Python syntax is clean!")
        except SyntaxError as e:
            error_msg = f"SyntaxError on line {e.lineno}, col {e.offset}: {e.msg}\nCode: {e.text}"
            errors.append(error_msg)
            logger.warning(error_msg)
        return errors

    def format_code(self, code_string: str) -> str:
        """
        Formats Python code using Ruff's formatter.

        Runs ``code_string`` through `ruff format -` (reading from and
        writing to stdio, so no temporary files are needed) at this
        formatter's configured `line_length`.

        Args:
            code_string: The Python source code to format, as a string.

        Returns:
            The Ruff-formatted source code.

        Raises:
            RuntimeError: If Ruff fails to format the code (e.g. a syntax
                error) — check with `view_errors` first if needed.

        Example:
            ```python
            fmt = PythonFormatter(line_length=100)
            clean = fmt.format_code("x={'a':1,'b':2}")  # 'x = {"a": 1, "b": 2}\\n'
            ```
        """
        logger.info("Formatting Python string...")

        result = subprocess.run(
            [_RUFF_BIN, "format", f"--line-length={self.line_length}", "-"],
            input=code_string,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            error_msg = f"Ruff formatting failed (check for syntax errors first): {result.stderr.strip()}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        return result.stdout
