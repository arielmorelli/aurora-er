"""Construction-time checks shared by DTOs."""

import math
from collections.abc import Iterable
from datetime import datetime


class InvalidDTOError(ValueError):
    """Raised when a DTO is constructed with values that violate its invariants."""


def require(condition: bool, message: str) -> None:
    """Raise :class:`InvalidDTOError` with ``message`` unless ``condition`` holds."""
    if not condition:
        raise InvalidDTOError(message)


def is_timezone_aware(moment: datetime) -> bool:
    """Whether ``moment`` carries a timezone that resolves to a UTC offset."""
    return moment.tzinfo is not None and moment.utcoffset() is not None


def are_finite(values: Iterable[float]) -> bool:
    """Whether every value is a finite number (no NaN or infinity)."""
    return all(math.isfinite(value) for value in values)
