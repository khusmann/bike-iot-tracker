#!/usr/bin/env python3
"""
BLE test client for BikeTracker firmware

This script connects to the ESP32 BikeTracker device and subscribes to
Cycling Speed and Cadence (CSC) notifications.

Requirements:
    pip install bleak

Usage:
    python test_ble_client.py
"""

import asyncio
import struct
from typing import Optional
from bleak import BleakScanner, BleakClient


# BLE Service and Characteristic UUIDs
CSC_SERVICE_UUID = "00001816-0000-1000-8000-00805f9b34fb"  # 0x1816
CSC_MEASUREMENT_UUID = "00002a5b-0000-1000-8000-00805f9b34fb"  # 0x2A5B

# Device name to search for
DEVICE_NAME = "BikeTracker"


class CSCMeasurement:
    """Parsed CSC Measurement data"""

    def __init__(self, flags: int, cumulative_revolutions: int, last_event_time: int):
        self.flags = flags
        self.cumulative_revolutions = cumulative_revolutions
        self.last_event_time = last_event_time

    @classmethod
    def from_bytes(cls, data: bytes) -> 'CSCMeasurement':
        """Parse CSC Measurement from BLE notification data"""
        if len(data) < 7:
            raise ValueError(f"Invalid CSC data length: {len(data)}")

        flags, cumulative_revs, last_time = struct.unpack('<BIH', data[:7])
        return cls(flags, cumulative_revs, last_time)

    def __str__(self) -> str:
        return (
            f"CSCMeasurement(revs={self.cumulative_revolutions}, "
            f"time={self.last_event_time}, flags=0x{self.flags:02x})"
        )


class CSCClient:
    """BLE client for CSC service"""

    def __init__(self):
        self.client: Optional[BleakClient] = None
        self.last_measurement: Optional[CSCMeasurement] = None
        self.last_time: Optional[int] = None

    def notification_handler(self, sender, data: bytearray) -> None:
        """Handle incoming CSC notifications"""
        try:
            measurement = CSCMeasurement.from_bytes(bytes(data))
            print(f"\n[Notification] {measurement}")

            # Calculate cadence if we have a previous measurement
            if self.last_measurement is not None:
                rev_delta = measurement.cumulative_revolutions - self.last_measurement.cumulative_revolutions

                # Handle 16-bit timer wraparound
                time_delta = measurement.last_event_time - self.last_time
                if time_delta < 0:
                    time_delta += 65536

                if time_delta > 0 and rev_delta > 0:
                    # Convert to RPM: (revolutions / time_in_1024ths_sec) * (1024 sec/unit) * (60 sec/min)
                    cadence_rpm = (rev_delta * 1024 * 60) / time_delta
                    print(f"[Cadence] {cadence_rpm:.1f} RPM")

            self.last_measurement = measurement
            self.last_time = measurement.last_event_time

        except Exception as e:
            print(f"Error parsing notification: {e}")

    async def find_device(self) -> str:
        """Scan for BikeTracker device and return its address"""
        print(f"Scanning for '{DEVICE_NAME}'...")

        devices = await BleakScanner.discover(timeout=10.0)

        for device in devices:
            if device.name == DEVICE_NAME:
                print(f"Found {DEVICE_NAME} at {device.address}")
                return device.address

        raise RuntimeError(f"Could not find device '{DEVICE_NAME}'")

    async def connect_and_monitor(self) -> None:
        """Connect to device and monitor CSC notifications"""

        # Find device
        address = await self.find_device()

        # Connect
        print(f"Connecting to {address}...")
        async with BleakClient(address) as client:
            self.client = client
            print(f"Connected: {client.is_connected}")

            # Print services for debugging
            print("\nDiscovered services:")
            for service in client.services:
                print(f"  Service: {service.uuid}")
                for char in service.characteristics:
                    props = ",".join(char.properties)
                    print(f"    Characteristic: {char.uuid} ({props})")

            # Subscribe to CSC Measurement notifications
            print(f"\nSubscribing to CSC Measurement ({CSC_MEASUREMENT_UUID})...")
            await client.start_notify(CSC_MEASUREMENT_UUID, self.notification_handler)

            print("Monitoring notifications (Ctrl+C to stop)...")
            print("Start pedaling to see data!\n")

            # Keep connection alive
            try:
                while True:
                    await asyncio.sleep(1.0)
            except KeyboardInterrupt:
                print("\nStopping...")
            finally:
                await client.stop_notify(CSC_MEASUREMENT_UUID)


async def main() -> None:
    """Main entry point"""
    client = CSCClient()
    await client.connect_and_monitor()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
    except Exception as e:
        print(f"\nError: {e}")
