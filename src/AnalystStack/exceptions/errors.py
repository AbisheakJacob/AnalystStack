class DataPackageError(Exception):
    """Base exception for the package."""


class ConfigurationError(DataPackageError):
    """Raised when configuration/settings are invalid or missing."""


class ConnectionError(DataPackageError):
    """Raised when authentication or client initialization fails."""


class QueryExecutionError(DataPackageError):
    """Raised when a SQL query or DataFrame write operation fails."""


class ValidationError(DataPackageError):
    """Raised when input validation fails (e.g., malformed table names)."""


class PathPolicyError(DataPackageError):
    """Raised when a file path is refused by the workspace path policy."""


class ReadOnlyViolationError(ValidationError):
    """Raised when SQL is refused because it is not a single, side-effect-free read."""
