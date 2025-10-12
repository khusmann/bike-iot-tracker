# Tasks

Tasks for **Stage 2: BLE Proof-of-Concept**

## Firmware Tasks

- [x] Set up aioble library in MicroPython environment
- [ ] Implement BLE peripheral initialization
- [ ] Create Cycling Speed and Cadence Service (UUID 0x1816)
- [ ] Implement CSC Measurement characteristic with notification support
- [ ] Track cumulative crank revolution count
- [ ] Track crank event timing (last crank event time in 1/1024 second units)
- [ ] Format CSC Measurement data per BLE spec (flags + cumulative revs + last
      event time)
- [ ] Broadcast CSC notifications on each crank rotation
- [ ] Test BLE + WiFi coexistence for WebREPL development
- [ ] Add BLE device name advertising

## Android App Tasks

### Project Setup

- [ ] Create new Android project with Kotlin
- [ ] Add BLE permissions to manifest (BLUETOOTH_SCAN, BLUETOOTH_CONNECT, etc.)
- [ ] Set up basic project structure with functional architecture

### BLE Implementation

- [ ] Implement BLE scanner with CSC service UUID filter (0x1816)
- [ ] Create BLE connection manager
- [ ] Subscribe to CSC Measurement characteristic notifications
- [ ] Parse CSC Measurement data (cumulative revolutions, last event time)
- [ ] Calculate instantaneous cadence from CSC data

### UI

- [ ] Create main activity with connection status indicator
- [ ] Display current cadence (RPM)
- [ ] Display total revolution count
- [ ] Show BLE connection state (scanning/connected/disconnected)
- [ ] Add simple styling for readability

### Testing

- [ ] Test BLE connection reliability
- [ ] Verify cadence calculations match physical pedaling rate
- [ ] Test reconnection after connection loss
- [ ] Verify data accuracy during continuous pedaling

## Documentation

- [ ] Document CSC profile implementation details
- [ ] Add setup instructions for running the Android app
- [ ] Document known limitations or issues
