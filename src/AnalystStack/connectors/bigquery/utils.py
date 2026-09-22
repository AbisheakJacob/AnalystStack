"""BigQuery-specific text parsing and helper functions."""


def construct_full_table_id(project_id: str, schema: str, table_id: str) -> str:
    """Builds a backtick-quoted ``project.dataset.table`` reference for BigQuery Standard SQL.

    Args:
        project_id: The GCP project the table lives in.
        schema: The BigQuery dataset the table lives in.
        table_id: The table name.

    Returns:
        A string like `` `project.dataset.table` ``, safe to interpolate directly into a
        BigQuery Standard SQL query.
    """
    return f"`{project_id}.{schema}.{table_id}`"
