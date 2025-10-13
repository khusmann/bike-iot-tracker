from __future__ import annotations

import asyncio
import network
import ntptime
import typing as t
import uos
from machine import Pin
from time import localtime

# LED blink patterns (sequence of on/off durations in seconds)
SIMPLE_BLINK_PATTERN = [0.5, 0.5]  # Simple blink: on 0.5s, off 0.5s
DOUBLE_BLINK_PATTERN = [0.1, 0.1, 0.1, 0.7]  # Double-blink with pause


def format_time_hms(time_tuple: t.Tuple[int, int, int, int, int, int, int, int]) -> str:
    """Format a time tuple as HH:MM:SS string.

    Args:
        time_tuple: Time tuple from localtime().

    Returns:
        Formatted time string in HH:MM:SS format.
    """
    return f"{time_tuple[3]:02d}:{time_tuple[4]:02d}:{time_tuple[5]:02d}"


def log(message: str) -> None:
    """Log a message with timestamp prefix.

    Args:
        message: The message to log.
    """
    timestamp = format_time_hms(localtime())
    print(f"[{timestamp}] {message}")


async def blink_led(
    led: t.Optional[Pin],
    pattern: t.Sequence[float]
) -> None:
    """Blink LED following a pattern of on/off durations.

    Args:
        led: Optional LED pin to blink (no-op if None).
        pattern: Sequence of durations in seconds, alternating between on and off.
                 First duration is on-time, second is off-time, etc.
                 Example: [0.5, 0.5] for simple blink.
                 Example: [0.1, 0.1, 0.1, 0.7] for double-blink with pause.
    """
    for i, duration in enumerate(pattern):
        # Odd indices (0, 2, 4...) are on-time, even indices (1, 3, 5...) are off-time
        if led is not None:
            led.value(i % 2)
        await asyncio.sleep(duration)


async def ensure_wifi_connected(led: t.Optional[Pin] = None) -> network.WLAN:
    """Ensure WiFi is connected, retrying until successful.

    If WiFi is not connected, blink the LED (if provided) and keep retrying.

    Args:
        led: Optional LED pin to blink while waiting for connection.

    Returns:
        Connected WLAN interface.
    """
    wlan = network.WLAN(network.STA_IF)

    retry_count = 0
    while not wlan.isconnected():
        retry_count += 1
        log(f"WiFi not connected. Attempt #{retry_count} to reconnect...")

        await blink_led(led, SIMPLE_BLINK_PATTERN)

    log(f"WiFi connected: {wlan.ifconfig()}")
    return wlan


async def sync_ntp_time(led: t.Optional[Pin] = None) -> None:
    """Synchronize system time via NTP.

    On failure, enters an infinite error state with a distinct LED pattern
    (rapid double-blink).

    Args:
        led: Optional LED pin for error indication.
    """
    try:
        log("Setting time via NTP...")
        ntptime.settime()
        # Display current time
        current_time = localtime()
        log(
            f"NTP time synchronized successfully: {current_time[0]}-{current_time[1]:02d}-{current_time[2]:02d} {current_time[3]:02d}:{current_time[4]:02d}:{current_time[5]:02d} UTC"
        )
    except Exception as e:
        log(f"Failed to sync NTP time: {e}")
        # Enter error state with distinct LED pattern (rapid double-blink)
        log("Entering NTP error state...")
        while True:
            await blink_led(led, DOUBLE_BLINK_PATTERN)


def atomic_write(filename: str, text: str, temp_file_ext: str = '.tmp') -> bool:
    """Write text to a file using atomic write pattern.

    Atomic write pattern:
    1. Write to temporary file
    2. Rename temporary file to target (atomic operation on most filesystems)

    Args:
        filename: Target file path.
        text: Text content to write.
        temp_file_ext: Extension for temporary file (default: '.tmp').

    Returns:
        True if write successful, False otherwise.
    """

    temp_file = filename + temp_file_ext

    try:
        # Write to temporary file
        with open(temp_file, 'w') as f:
            f.write(text)

        try:
            # Atomic rename
            uos.rename(temp_file, filename)
        except Exception as e:
            log(f"Error during atomic rename: {e}")
            return False

        return True

    except Exception as e:
        log(f"Error writing file {filename}: {e}")
        return False

    finally:
        # Clean up temp file if it still exists
        try:
            uos.remove(temp_file)
        except OSError:
            pass  # Temp file doesn't exist, that's fine
