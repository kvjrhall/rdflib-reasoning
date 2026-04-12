def not_none[T](value: T | None, message: str = "Value cannot be None") -> T:
    if value is None:
        raise ValueError(message)
    return value
