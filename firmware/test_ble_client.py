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
SESSION_RANGE_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"
SESSION_DATA_UUID = "0000ff02-0000-1000-8000-00805f9b34fb"
MARK_SYNCED_UUID = "0000ff03-0000-1000-8000-00805f9b34fb"

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
    """BLE client for Sync service"""

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

    async def read_session_range(self, client: BleakClient) -> dict:
        """Read Session Range characteristic.

        Returns:
            Dictionary with 'start' and 'count' keys.
        """
        print(f"\nReading Session Range ({SESSION_RANGE_UUID})...")
        data = await client.read_gatt_char(SESSION_RANGE_UUID)
        json_str = data.decode('utf-8')
        response = json.loads(json_str)
        print(f"Session Range: {response}")
        return response

    async def request_session(self, client: BleakClient, session_id: int) -> dict:
        """Request session data by writing session_id to Session Data characteristic.

        Protocol: Write session_id, then read the response.

        Args:
            client: BleakClient instance
            session_id: Session ID to request

        Returns:
            Dictionary with session data or error
        """
        print(f"\nRequesting session {session_id}...")

        # Pack session_id as uint16 little-endian
        request_data = struct.pack('<H', session_id)

        # Write session_id to Session Data characteristic
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

        if 'error' in response:
            print(f"  Error: {response['error']}")
        else:
            print(f"  Session data: {response}")

        return response

    async def mark_synced(self, client: BleakClient, session_id: int) -> dict:
        """Mark a session as synced.

        Protocol: Write session_id, then read the response.

        Args:
            client: BleakClient instance
            session_id: Session ID to mark as synced

        Returns:
            Dictionary with success status or error
        """
        print(f"Marking session {session_id} as synced...")

        # Pack session_id as uint16 little-endian
        request_data = struct.pack('<H', session_id)

        # Write session_id to Mark Synced characteristic
        await client.write_gatt_char(
            MARK_SYNCED_UUID,
            request_data,
            response=True
        )

        # Small delay to let the ESP32 process the request
        await asyncio.sleep(0.5)

        # Read the response from the same characteristic
        response_data = await client.read_gatt_char(MARK_SYNCED_UUID)

        # Parse JSON response
        json_str = response_data.decode('utf-8')
        response = json.loads(json_str)

        if 'error' in response:
            print(f"  Error: {response['error']}")
        else:
            print(f"  Success!")

        return response

    async def sync_all_sessions(self, client: BleakClient) -> None:
        """Orchestrate full sync flow: read range, request sessions, mark synced.

        Args:
            client: BleakClient instance
        """
        print("\n" + "="*60)
        print("SYNC PROTOCOL TEST")
        print("="*60)

        # Step 1: Read session range
        range_data = await self.read_session_range(client)
        start = range_data.get('start', 0)
        count = range_data.get('count', 0)

        if count == 0:
            print("\nNo unsynced sessions found.")
            return

        print(
            f"\nFound {count} unsynced sessions (IDs {start} to {start + count - 1})")

        # Step 2: Request each session
        synced_sessions = []
        for session_id in range(start, start + count):
            session_data = await self.request_session(client, session_id)

            if 'error' not in session_data:
                synced_sessions.append(session_data)

                # Step 3: Mark as synced
                await self.mark_synced(client, session_id)
            else:
                print(f"  Skipping session {session_id} due to error")

        # Print summary
        print("\n" + "="*60)
        print("SYNC SUMMARY")
        print("="*60)
        print(f"Total sessions synced: {len(synced_sessions)}")
        for session in synced_sessions:
            duration = session['end_time'] - session['start_time']
            print(
                f"  Session {session['id']}: {session['revolutions']} revs, {duration}s duration")
        print("="*60 + "\n")

    async def test_sync(self) -> None:
        """Connect to device and test sync protocol"""

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
