"""Small shared helpers for middleware implementations."""


def not_none[T](value: T | None, message: str = "Value cannot be None") -> T:
    """Return ``value`` or raise ``ValueError`` when it is ``None``."""
    if value is None:
        raise ValueError(message)
    return value
