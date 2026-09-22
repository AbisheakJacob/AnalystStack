"""Reshape DataFrames between tidy (long) and normal (wide) layouts.

See :func:`~AnalystStack.tidy.reshape.to_tidy` and
:func:`~AnalystStack.tidy.reshape.from_tidy`.
"""

from AnalystStack.tidy.reshape import from_tidy, to_tidy

__all__ = ["to_tidy", "from_tidy"]
