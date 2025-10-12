# Stages

This outlines the main implementation stages for this project.

Tasks of the current stage will go in tasks.md

## Stage 1: Basic Setup (Completed)

- Firmware-only implementation
- LED toggles on crank rotation detection
- WiFi with WebREPL for OTA updates

## Stage 2: BLE Proof-of-Concept (Current)

**Firmware:**

- Implement BLE peripheral with Cycling Speed and Cadence (CSC) service
- Broadcast crank revolution count and timing via CSC notifications

**Android App:**

- Connect to ESP32 via BLE on app launch
- Display live CSC telemetry stream

## Stage 3: TBD
