# primitives/__init__.pyi - Type stubs for primitives package

from typing import Any, Callable, Tuple

# Re-export classes from submodules (matching lazy-loading behavior)
from primitives.pushbutton import Pushbutton, ESP32Touch

# Type for coroutines
type_coro: type

def launch(func: Callable[..., Any], tup_args: Tuple[Any, ...]) -> Any:
    """
    Launch a function or coroutine with arguments.

    If a callback is passed, run it and return.
    If a coroutine is passed, initiate it and return.
    """
    ...

def set_global_exception() -> None:
    """Set global exception handler for asyncio loop."""
    ...

class Delay_ms:
    """Delay timer class."""
    def __init__(self, func: Callable[..., Any] | None = None, args: Tuple[Any, ...] = ...) -> None: ...
    def trigger(self, duration: int) -> None: ...
    def stop(self) -> None: ...
    def __call__(self) -> bool: ...
    def callback(self, func: Callable[..., Any], args: Tuple[Any, ...] = ...) -> None: ...

__all__ = ["Pushbutton", "ESP32Touch", "Delay_ms", "launch", "set_global_exception", "type_coro"]
