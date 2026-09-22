"""Snowflake connector: `SnowflakeConnector` and its supporting client/query/metadata/
profiling managers.
"""

# Import the main class using a relative import (.)
from .connector import SnowflakeConnector

# The __all__ variable strictly defines what gets exported if someone runs `from ... import *`
__all__ = ["SnowflakeConnector"]
