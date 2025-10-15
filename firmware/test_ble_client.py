#!/usr/bin/env python3
"""
BLE test client for BikeTracker firmware

This script connects to the ESP32 BikeTracker device and either:
1. Monitors CSC notifications (--monitor mode, default)
2. Tests the sync protocol (--sync mode)

Requirements:
    pip install bleak

Usage:
    python test_ble_client.py          # Monitor CSC notifications
    python test_ble_client.py --sync   # Test sync protocol
"""

import argparse
import asyncio
import json
import struct
from typing import Optional
from bleak import BleakScanner, BleakClient


# BLE Service and Characteristic UUIDs
# CSC Service
CSC_SERVICE_UUID = "00001816-0000-1000-8000-00805f9b34fb"  # 0x1816
CSC_MEASUREMENT_UUID = "00002a5b-0000-1000-8000-00805f9b34fb"  # 0x2A5B

# Sync Service
SYNC_SERVICE_UUID = "0000ff00-0000-1000-8000-00805f9b34fb"
SESSION_DATA_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"

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

    def notification_handler(self, sender, data: bytearray) -> None:
        """Handle incoming CSC notifications"""
        try:
            measurement = CSCMeasurement.from_bytes(bytes(data))
            print(f"[Notification] {measurement}")

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
            print(
                f"\nSubscribing to CSC Measurement ({CSC_MEASUREMENT_UUID})...")
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


class SyncClient:
    """BLE client for Sync service using timestamp-based protocol"""

    def __init__(self):
        self.client: Optional[BleakClient] = None

    async def find_device(self) -> str:
        """Scan for BikeTracker device and return its address"""
        print(f"Scanning for '{DEVICE_NAME}'...")

        devices = await BleakScanner.discover(timeout=10.0)

        for device in devices:
            if device.name == DEVICE_NAME:
                print(f"Found {DEVICE_NAME} at {device.address}")
                return device.address

        raise RuntimeError(f"Could not find device '{DEVICE_NAME}'")

    async def request_next_session(
        self, client: BleakClient, last_synced_start_time: int
    ) -> dict:
        """Request next session after the given timestamp.

        Protocol: Write uint32 lastSyncedStartTime, read JSON response.

        Args:
            client: BleakClient instance
            last_synced_start_time: Unix timestamp of last synced session (0 for first)

        Returns:
            Dictionary with:
              - "session": Session data dict (or None if no more sessions)
              - "remaining_sessions": Count of remaining sessions
        """
        # Pack lastSyncedStartTime as uint32 little-endian
        request_data = struct.pack('<I', last_synced_start_time)

        # Write timestamp to Session Data characteristic
        await client.write_gatt_char(
            SESSION_DATA_UUID,
            request_data,
            response=True
        )

        # Small delay to let the ESP32 process the request
        await asyncio.sleep(0.5)

        # Read the response from the same characteristic
        response_data = await client.read_gatt_char(SESSION_DATA_UUID)

        # Parse JSON response
        json_str = response_data.decode('utf-8')
        response = json.loads(json_str)

        return response

    async def sync_all_sessions(
        self, client: BleakClient, start_from: int = 0
    ) -> list[dict]:
        """Orchestrate full sync flow using timestamp-based protocol.

        Args:
            client: BleakClient instance
            start_from: Unix timestamp to start syncing from (0 = all sessions)

        Returns:
            List of synced session dictionaries
        """
        print("\n" + "="*60)
        print("SYNC PROTOCOL TEST (Timestamp-Based)")
        print("="*60)
        print(f"Syncing sessions since timestamp: {start_from}")

        synced_sessions = []
        last_synced = start_from

        # Client-driven loop
        while True:
            print(f"\nRequesting sessions after {last_synced}...")

            response = await self.request_next_session(client, last_synced)

            # Check for errors
            if 'error' in response:
                print(f"Error: {response['error']}")
                break

            # Check if we're done
            session = response.get('session')
            remaining = response.get('remaining_sessions', 0)

            if session is None:
                print("No more sessions to sync.")
                break

            # Got a session!
            print(f"Received session {session['start_time']}")
            print(f"  Revolutions: {session['revolutions']}")
            print(f"  Duration: {session['end_time'] - session['start_time']}s")
            print(f"  Remaining: {remaining}")

            synced_sessions.append(session)

            # Update our pointer for next request
            last_synced = session['start_time']

        # Print summary
        print("\n" + "="*60)
        print("SYNC SUMMARY")
        print("="*60)
        print(f"Total sessions synced: {len(synced_sessions)}")
        for session in synced_sessions:
            duration = session['end_time'] - session['start_time']
            print(
                f"  Session {session['start_time']}: {session['revolutions']} revs, {duration}s")
        print("="*60 + "\n")

        return synced_sessions

    async def test_sync(self) -> None:
        """Connect to device and test sync protocol"""

        # Find device
        address = await self.find_device()

        # Connect
        print(f"Connecting to {address}...")
        async with BleakClient(address) as client:
            self.client = client
            print(f"Connected: {client.is_connected}")

            # MTU check (if available)
            # Response size ~102 bytes + overhead requires ~185+ bytes MTU
            # Note: bleak handles MTU negotiation automatically on most platforms
            print("\nNote: MTU negotiation is handled automatically by bleak")
            print("Response size ~102 bytes requires MTU >= 185 bytes")

            # Print services for debugging
            print("\nDiscovered services:")
            for service in client.services:
                print(f"  Service: {service.uuid}")
                for char in service.characteristics:
                    props = ",".join(char.properties)
                    print(f"    Characteristic: {char.uuid} ({props})")

            # Run sync protocol
            await self.sync_all_sessions(client)

            print("Sync test complete!")


async def main(mode: str) -> None:
    """Main entry point

    Args:
        mode: Either 'monitor' for CSC monitoring or 'sync' for sync protocol test
    """
    if mode == 'sync':
        client = SyncClient()
        await client.test_sync()
    else:  # monitor mode (default)
        client = CSCClient()
        await client.connect_and_monitor()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BLE test client for BikeTracker firmware"
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Test sync protocol (default: monitor CSC notifications)"
    )

    args = parser.parse_args()
    mode = 'sync' if args.sync else 'monitor'

    print(f"Running mode {mode}")

    try:
        asyncio.run(main(mode))
    except KeyboardInterrupt:
        print("\nShutdown complete")
    except Exception as e:
        print(f"\nError: {e}")
