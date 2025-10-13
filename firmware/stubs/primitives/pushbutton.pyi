# primitives/pushbutton.pyi - Type stubs for pushbutton module

from typing import Any, Callable, Tuple, TypeVarTuple, TypeVar, Unpack
import asyncio


P = TypeVarTuple("P")
R = TypeVar("R")


class Pushbutton:
    """
    Asynchronous debounced pushbutton handler.

    Provides callbacks for press, release, long press, and double-click events.
    Runs an internal asyncio task for debouncing and state tracking.

    Class attributes:
        debounce_ms: Debounce delay in milliseconds (default: 50)
        long_press_ms: Long press threshold in milliseconds (default: 1000)
        double_click_ms: Double-click timeout in milliseconds (default: 400)

    Instance attributes (when using Event mode):
        press: asyncio.Event set on button press (if press_func(None) called)
        release: asyncio.Event set on button release (if release_func(None) called)
        double: asyncio.Event set on double-click (if double_func(None) called)
        long: asyncio.Event set on long press (if long_func(None) called)
    """

    debounce_ms: int
    long_press_ms: int
    double_click_ms: int

    # Event attributes (only exist if configured with func=None)
    press: asyncio.Event
    release: asyncio.Event
    double: asyncio.Event
    long: asyncio.Event

    def __init__(
        self,
        pin: Any,
        suppress: bool = False,
        sense: int | None = None
    ) -> None:
        """
        Initialize pushbutton handler.

        Args:
            pin: Machine Pin object for the button
            suppress: If True, suppress release callback when long press or
                     double-click is triggered
            sense: Logical sense (0=active low, 1=active high). If None,
                  determined from pin's initial state
        """
        ...

    def press_func(
        self,
        func: Callable[[Unpack[P]], R] | None | bool = False,
        args: Tuple[Unpack[P]] = ()
    ) -> None:
        """
        Set callback for button press event.

        Args:
            func: Callback function or coroutine to call on press.
                 If None, creates self.press Event for await pattern.
                 If False, clears the callback.
            args: Tuple of arguments to pass to callback
        """
        ...

    def release_func(
        self,
        func: Callable[[Unpack[P]], R] | None | bool = False,
        args: Tuple[Unpack[P]] = ()
    ) -> None:
        """
        Set callback for button release event.

        Args:
            func: Callback function or coroutine to call on release.
                 If None, creates self.release Event for await pattern.
                 If False, clears the callback.
            args: Tuple of arguments to pass to callback
        """
        ...

    def double_func(
        self,
        func: Callable[[Unpack[P]], R] | None | bool = False,
        args: Tuple[Unpack[P]] = ()
    ) -> None:
        """
        Set callback for double-click event.

        Args:
            func: Callback function or coroutine to call on double-click.
                 If None, creates self.double Event for await pattern.
                 If False, clears the callback.
            args: Tuple of arguments to pass to callback
        """
        ...

    def long_func(
        self,
        func: Callable[[Unpack[P]], R] | None | bool = False,
        args: Tuple[Unpack[P]] = ()
    ) -> None:
        """
        Set callback for long press event.

        Args:
            func: Callback function or coroutine to call on long press.
                 If None, creates self.long Event for await pattern.
                 If False, clears the callback.
            args: Tuple of arguments to pass to callback
        """
        ...

    def rawstate(self) -> bool:
        """
        Get current non-debounced logical button state.

        Returns:
            True if button is pressed, False if released
        """
        ...

    def __call__(self) -> bool:
        """
        Get current debounced button state.

        Returns:
            True if button is pressed, False if released
        """
        ...

    def deinit(self) -> None:
        """Cancel the internal asyncio task and clean up."""
        ...


class ESP32Touch(Pushbutton):
    """
    ESP32 capacitive touch sensor handler.

    Extends Pushbutton to work with ESP32 TouchPad sensors instead of
    physical buttons.
    """

    thresh: int

    @classmethod
    def threshold(cls, val: int) -> None:
        """
        Set touch detection threshold as percentage.

        Args:
            val: Threshold value (1-99)

        Raises:
            ValueError: If val is not in range 1-99
        """
        ...

    def __init__(self, pin: Any, suppress: bool = False) -> None:
        """
        Initialize ESP32 touch sensor handler.

        Args:
            pin: Machine Pin object for the touch sensor
            suppress: If True, suppress release callback when long press or
                     double-click is triggered

        Raises:
            ValueError: If pin is not a valid touch-capable pin
        """
        ...

    def rawstate(self) -> bool:
        """
        Get current non-debounced touch sensor state.

        Returns:
            True if sensor is touched, False otherwise
        """
        ...
