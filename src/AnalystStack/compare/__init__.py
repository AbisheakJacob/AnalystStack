"""Compare two DataFrames key-by-key, and generate one-call summary profiles.

Answers two everyday analyst questions: *"how do these two DataFrames differ?"* (see
:func:`~AnalystStack.compare.comparison.compare_dataframes`) and *"what does this DataFrame
look like?"* (see :func:`~AnalystStack.compare.summary.summarize`).
"""

from AnalystStack.compare.comparison import ComparisonResult, compare_dataframes
from AnalystStack.compare.summary import summarize

__all__ = ["ComparisonResult", "compare_dataframes", "summarize"]
