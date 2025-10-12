import asyncio
import struct
from machine import Pin
from time import ticks_ms, ticks_diff
import bluetooth
import aioble

# Hardware configuration
led = Pin(4, Pin.OUT)
reed = Pin(5, Pin.IN, Pin.PULL_UP)

# BLE Service and Characteristic UUIDs
# Cycling Speed and Cadence Service
CSC_SERVICE_UUID = bluetooth.UUID(0x1816)
# CSC Measurement Characteristic
CSC_MEASUREMENT_UUID = bluetooth.UUID(0x2A5B)

# Device name for advertising
DEVICE_NAME = "BikeTracker"

# Debounce configuration
DEBOUNCE_MS = 50

# CSC timing constants
# Time is measured in 1/1024 second units per BLE CSC spec
TIME_UNIT_HZ = 1024


# Immutable telemetry state
class TelemetryState:
    """Immutable state for crank telemetry tracking"""

    def __init__(
        self,
        cumulative_revolutions: int = 0,
        last_event_time: int = 0,
        last_physical_time_ms: int = 0
    ):
        self.cumulative_revolutions = cumulative_revolutions
        self.last_event_time = last_event_time
        self.last_physical_time_ms = last_physical_time_ms

    def with_new_revolution(self, current_time_ms: int) -> 'TelemetryState':
        """Return new state with incremented revolution count"""
        # Convert milliseconds to 1/1024 second units
        time_in_units = (current_time_ms * TIME_UNIT_HZ) // 1000
        # Wrap at 16 bits (0-65535) per BLE spec
        wrapped_time = time_in_units & 0xFFFF

        return TelemetryState(
            cumulative_revolutions=(
                self.cumulative_revolutions + 1) & 0xFFFFFFFF,  # Wrap at 32 bits
            last_event_time=wrapped_time,
            last_physical_time_ms=current_time_ms
        )

    def to_csc_measurement(self) -> bytes:
        """
        Format state as CSC Measurement per BLE spec

        Format:
        - Byte 0: Flags (bit 1 = crank revolution data present)
        - Bytes 1-4: Cumulative crank revolutions (uint32, little-endian)
        - Bytes 5-6: Last crank event time (uint16, little-endian, 1/1024 sec units)
        """
        flags = 0x02  # Bit 1: Crank Revolution Data Present
        return struct.pack(
            '<BIH',
            flags,
            self.cumulative_revolutions,
            self.last_event_time
        )


# Global state (will be updated functionally)
telemetry_state = TelemetryState()
new_revolution_event = asyncio.Event()
last_debounce_time_ms = 0


def reed_irq_handler(pin: Pin) -> None:
    """IRQ handler for reed switch - updates telemetry on crank rotation"""
    global telemetry_state, last_debounce_time_ms

    current_time_ms = ticks_ms()

    # Debounce check
    if ticks_diff(current_time_ms, last_debounce_time_ms) < DEBOUNCE_MS:
        return

    last_debounce_time_ms = current_time_ms

    # Update telemetry state (functional style)
    telemetry_state = telemetry_state.with_new_revolution(current_time_ms)

    # Toggle LED for visual feedback
    led.value(not led.value())

    # Signal that new data is available
    new_revolution_event.set()

    print(f"Revolution {telemetry_state.cumulative_revolutions}")


async def advertise_and_serve() -> None:
    """Main BLE advertising and connection serving loop"""

    # Register CSC Service
    csc_service = aioble.Service(CSC_SERVICE_UUID)

    # Register CSC Measurement Characteristic (notify only)
    csc_measurement_char = aioble.Characteristic(
        csc_service,
        CSC_MEASUREMENT_UUID,
        read=False,
        write=False,
        notify=True,
        indicate=False
    )

    # Register the service
    aioble.register_services(csc_service)

    print("BLE services registered")

    while True:
        print(f"Advertising as '{DEVICE_NAME}'...")

        async with await aioble.advertise(
            interval_us=250_000,  # 250ms advertising interval
            name=DEVICE_NAME,
            services=[CSC_SERVICE_UUID],
            appearance=0x0000,  # Generic appearance
        ) as connection:
            print(f"Connected to {connection.device}")

            try:
                # Connection handler loop
                while connection.is_connected():
                    # Wait for new revolution event or timeout
                    try:
                        await asyncio.wait_for(
                            new_revolution_event.wait(),
                            timeout=30.0
                        )
                        new_revolution_event.clear()

                        # Send notification with latest telemetry
                        measurement_data = telemetry_state.to_csc_measurement()
                        csc_measurement_char.notify(
                            connection, measurement_data)
                        print(
                            f"Sent notification: rev={telemetry_state.cumulative_revolutions}")

                    except asyncio.TimeoutError:
                        # Periodic keepalive - send current state even if no new data
                        measurement_data = telemetry_state.to_csc_measurement()
                        csc_measurement_char.notify(
                            connection, measurement_data)
                        print("Keepalive notification sent")

            except Exception as e:
                print(f"Connection error: {e}")
            finally:
                print("Disconnected")


async def main() -> None:
    """Main entry point - start BLE peripheral"""

    # Enable reed switch IRQ
    reed.irq(trigger=Pin.IRQ_FALLING, handler=reed_irq_handler)

    print("Starting BikeTracker firmware...")
    print(f"LED on GPIO {led}")
    print(f"Reed switch on GPIO {reed}")

    # Start BLE peripheral
    await advertise_and_serve()


# Run the async main loop
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Shutting down...")
