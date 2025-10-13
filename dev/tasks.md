# Tasks

Tasks for **Stage 2: BLE Proof-of-Concept**

## Firmware Tasks

- [x] Set up aioble library in MicroPython environment
- [x] Implement BLE peripheral initialization
- [x] Create Cycling Speed and Cadence Service (UUID 0x1816)
- [x] Implement CSC Measurement characteristic with notification support
- [x] Track cumulative crank revolution count
- [x] Track crank event timing (last crank event time in 1/1024 second units)
- [x] Format CSC Measurement data per BLE spec (flags + cumulative revs + last
      event time)
- [x] Broadcast CSC notifications on each crank rotation
- [ ] Test BLE + WiFi coexistence for WebREPL development
- [x] Add BLE device name advertising
- [x] Write a simple Python script to test firmware (from a computer)

## Android App Tasks

### Project Setup

- [x] Create new Android project with Kotlin
- [x] Add BLE permissions to manifest (BLUETOOTH_SCAN, BLUETOOTH_CONNECT, etc.)
- [x] Set up basic project structure with functional architecture

### BLE Implementation

- [x] Implement BLE scanner with CSC service UUID filter (0x1816)
- [x] Create BLE connection manager
- [x] Subscribe to CSC Measurement characteristic notifications
- [x] Parse CSC Measurement data (cumulative revolutions, last event time)
- [x] Calculate instantaneous cadence from CSC data

### UI

- [x] Create main activity with connection status indicator
- [x] Display current cadence (RPM)
- [x] Display total revolution count
- [x] Show BLE connection state (scanning/connected/disconnected)
- [x] Add simple styling for readability

### Testing

- [ ] Test BLE connection reliability
- [ ] Verify cadence calculations match physical pedaling rate
- [ ] Test reconnection after connection loss
- [ ] Verify data accuracy during continuous pedaling

## Documentation

- [x] Document CSC profile implementation details
- [x] Add setup instructions for running the Android app
- [x] Document known limitations or issues
