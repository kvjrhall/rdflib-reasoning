import functools
from collections.abc import Callable
from typing import Any, Protocol, TypeVar, cast

from .facts import Fact

F = TypeVar("F", bound=Callable[..., Any])


class CallbackContext(Protocol):
    """
    Restricted, read-only interface passed to non-logical callbacks.

    Callback contexts are intentionally observational: they may expose tracing,
    metrics, or other side-channel recording, but they MUST NOT provide graph
    mutation operations.
    """

    def record(self, event: Any) -> None: ...


class CallbackAction:
    """
    A non-logical callback triggered by a completed match.

    Callback actions are observational hooks only; they are not an alternate
    inference channel and MUST NOT mutate graph state.
    """

    ...


def rule_action(undo: Callable | None = None, salience: int = 0):
    """
    Decorator to register a non-mutating callback attached to a rule match.

    The ``undo`` parameter is reserved for future callback-specific undo
    policy. Logical triple retraction is handled by the TMS path rather than
    by callback actions.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(context: CallbackContext, *args: Fact, **kwargs):
            return func(context, *args, **kwargs)

        return cast(F, wrapper)

    return decorator
