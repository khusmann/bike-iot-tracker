# Testing the BikeTracker Firmware

**Note:** All commands in this document assume you're running them from the `firmware/` directory.

## Overview

The firmware implements the Bluetooth Low Energy (BLE) Cycling Speed and Cadence
(CSC) Service, broadcasting crank revolution data to connected clients.

## Firmware Implementation

The firmware ([main.py](src/main.py)) provides:

- **BLE Peripheral**: Advertises as "BikeTracker" with CSC Service (UUID 0x1816)
- **CSC Measurement Characteristic**: Broadcasts notifications with:
  - Cumulative crank revolution count (32-bit, wraps at 4,294,967,295)
  - Last crank event time in 1/1024 second units (16-bit, wraps at 65,535)
- **Reed Switch Integration**: Detects crank rotations on GPIO 5 (with 50ms debounce)
- **Visual Feedback**: LED on GPIO 4 toggles on each crank rotation
- **Efficient Notifications**: Sends BLE notifications on every crank event plus
  30-second keepalive

## Testing with Python BLE Client

### Setup

Activate the Python virtual environment (this will create the venv if it doesn't exist and install dependencies):

```bash
source activate.sh
```

### Running the Test Client

The test client ([test_ble_client.py](test_ble_client.py)) will:

1. Scan for the "BikeTracker" BLE device
2. Connect to it
3. Subscribe to CSC Measurement notifications
4. Display revolution counts and calculated cadence (RPM)

Run the test client:

```bash
python test_ble_client.py
```

Expected output:

```
Scanning for 'BikeTracker'...
Found BikeTracker at XX:XX:XX:XX:XX:XX
Connecting to XX:XX:XX:XX:XX:XX...
Connected: True

Discovered services:
  Service: 00001816-0000-1000-8000-00805f9b34fb
    Characteristic: 00002a5b-0000-1000-8000-00805f9b34fb (notify)

Subscribing to CSC Measurement...
Monitoring notifications (Ctrl+C to stop)...
Start pedaling to see data!

[Notification] CSCMeasurement(revs=1, time=5234, flags=0x02)
[Notification] CSCMeasurement(revs=2, time=6891, flags=0x02)
[Cadence] 72.3 RPM
[Notification] CSCMeasurement(revs=3, time=8547, flags=0x02)
[Cadence] 72.5 RPM
...
```

## Testing BLE + WiFi Coexistence

The firmware should maintain WebREPL connectivity while BLE is active, allowing
for OTA updates during development.

To test:

1. Flash the firmware to ESP32
2. Connect to WebREPL (the device should connect to WiFi via boot.py)
3. Run the BLE test client from another machine
4. Verify:
   - BLE client successfully connects and receives notifications
   - WebREPL remains responsive
   - No connection drops or instability

## Known Limitations

- **Single Connection**: Only one BLE client can connect at a time (by design)
- **No Persistence**: Revolution count resets on device reboot
- **WiFi/BLE Coexistence**: May require testing for stability depending on ESP32
  WiFi/BLE usage patterns

## Next Steps

Once firmware testing is complete, the next phase is Android app development to:

1. Scan for and connect to the BikeTracker device
2. Subscribe to CSC notifications
3. Display live cadence and revolution data
4. Implement efficient background synchronization patterns
