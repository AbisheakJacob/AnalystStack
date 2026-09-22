import re


def parse_excel_cell(cell: str) -> tuple[int, int, str]:
    """
    Parses an Excel cell reference into 0-indexed row/column integers.

    Splits a cell reference like ``"C4"`` into its column-letter and row-number
    parts, converts the row number to a 0-indexed integer, and converts the
    column letter to a 0-indexed integer (``A`` -> 0, ``B`` -> 1, ..., ``Z`` ->
    25, ``AA`` -> 26, ...).

    Args:
        cell: An Excel cell reference, e.g. ``"C4"``. Case-insensitive.

    Returns:
        A 3-tuple of ``(row_index, col_index, col_letter)`` where ``row_index``
        and ``col_index`` are 0-indexed integers and ``col_letter`` is the
        upper-cased column letter(s) parsed from ``cell``.

    Raises:
        ValueError: If ``cell`` is not a valid Excel cell reference.

    Example:
        ```python
        parse_excel_cell("C4")  # -> (3, 2, "C")
        ```
    """
    match = re.match(r"([A-Za-z]+)([0-9]+)", cell.upper())
    if not match:
        raise ValueError(f"Invalid Excel cell reference: {cell}")

    col_letter, row_str = match.groups()
    row_idx = int(row_str) - 1  # 0-indexed

    # Convert Excel column letter to 0-indexed integer (A=0, B=1, Z=25, AA=26)
    col_idx = 0
    for char in col_letter:
        col_idx = col_idx * 26 + (ord(char) - ord("A") + 1)
    col_idx -= 1

    return row_idx, col_idx, col_letter
