from .reader import DataReader
from .writer import DataWriter


class DataIOManager:
    """Facade for all IO operations.

    Bundles a `DataReader` and a `DataWriter` behind two attributes, ``read`` and
    ``write``, so callers can perform every supported read/write operation through
    a single pre-instantiated object instead of importing and constructing the
    reader/writer classes themselves.

    Attributes:
        read: A `DataReader` instance exposing `DataReader.excel`,
            `DataReader.csv`, `DataReader.parquet`, and `DataReader.jinja`.
        write: A `DataWriter` instance exposing `DataWriter.excel`,
            `DataWriter.csv`, `DataWriter.markdown`, `DataWriter.txt`, and
            `DataWriter.clipboard`.

    Example:
        ```python
        from AnalystStack.io import io

        io.read.csv("data.csv")
        io.write.markdown(df, "table.md")
        ```
    """

    def __init__(self):
        self.read = DataReader()
        self.write = DataWriter()


# Instantiate it so users can just import the pre-configured object
io = DataIOManager()

__all__ = ["io"]
