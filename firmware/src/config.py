"""
Application configuration with dev/prod environment support.

Loads configuration from device.env and provides a singleton config instance
that can be imported throughout the application.

Environment variable ENV in device.env controls which profile is loaded:
- ENV=dev: Development settings (short timeouts, debug device name)
- ENV=prod (or not set): Production settings (standard timeouts)
"""
from udataclasses import dataclass


@dataclass
class Config:
    """Application configuration settings.

    Attributes:
        led_pin: GPIO pin number for status LED
        reed_pin: GPIO pin number for reed switch (crank sensor)
        idle_timeout_ms: Time in milliseconds before ending inactive session
        device_name: BLE advertising name for the device
        save_interval_s: Interval in seconds for periodic session saves
        session_min_duration_s: Minimum session duration in seconds (shorter sessions discarded)
        sessions_file: Filesystem path for session storage JSON file
        csc_notification_interval_s: Interval in seconds for BLE CSC notifications
    """
    # BLE Configuration
    device_name: str = "BikeTracker"  # BLE advertising name
    csc_notification_interval_s: int = 2  # CSC measurement notification interval
    ble_advertising_interval_us: int = 250_000  # 250ms advertising interval

    # Hardware Configuration
    led_pin: int = 4  # GPIO pin for status LED
    reed_pin: int = 5  # GPIO pin for reed switch (crank sensor)

    # Session Management
    # 5 minutes - time before ending inactive session
    session_idle_timeout_s: int = 5 * 60
    # 5 minutes - periodic save interval for active sessions
    session_save_interval_s: int = 5 * 60
    # 5 minutes - minimum session duration to keep
    session_min_duration_s: int = 5 * 60

    # Storage
    sessions_dir: str = "/sessions"  # Directory for session storage files


def _load_config(dev: bool = False) -> Config:
    """Load configuration with environment-specific overrides.

    Reads device.env and applies dev/prod profile settings.

    Returns:
        Config instance with appropriate settings for the environment.
    """
    config = Config()

    # Apply development environment overrides
    if dev:
        config.session_idle_timeout_s = 30  # 30 seconds for faster testing

    return config


# Singleton instance - created once at module import
config = _load_config()
