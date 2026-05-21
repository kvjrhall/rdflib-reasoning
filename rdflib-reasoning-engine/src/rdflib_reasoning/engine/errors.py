"""Base exception types for engine action and builtin failures."""


class ActionError(Exception):
    """Base exception for engine action failures."""


class RetractionError(ActionError):
    """Base exception for truth-maintenance retraction failures."""


class RetractionNotImplementedError(RetractionError):
    """Raised when a requested retraction operation is not implemented."""


class BuiltinError(Exception):
    """Base exception for builtin hook failures."""


class BuiltinInputError(BuiltinError, ValueError):
    """Raised when builtin hook arguments violate the hook contract."""
