# Bike Tracker Android App

Android companion app for the ESP32 bike tracker system. Connects via BLE to
receive real-time cycling telemetry.

## Features

- Real-time cadence display (RPM)
- Total revolution count tracking
- BLE connection status indicator
- Minimal battery usage with efficient BLE scanning
- Simple, clean UI

## Requirements

- Android 8.0 (API 26) or higher
- Device with BLE support
- Java 17 or higher for building

## Building

### Setup

The project uses the Gradle wrapper, so you don't need to install Gradle
manually. However, you need the Android SDK:

Create a `local.properties` file in the `android` directory:

```properties
sdk.dir=/path/to/your/Android/Sdk
```

Typical SDK locations:

- Linux: `~/Android/Sdk` or `$HOME/Android/Sdk`
- macOS: `~/Library/Android/sdk`
- Windows: `C:\Users\YourUsername\AppData\Local\Android\Sdk`

Note: `local.properties` is git-ignored and won't be committed to the repo.

### Command Line Build

```bash
# Build debug APK
./gradlew assembleDebug

# Install to connected device
./gradlew installDebug

# Build and install
./gradlew installDebug
```

The APK will be generated at: `app/build/outputs/apk/debug/app-debug.apk`

### Android Studio

1. Open Android Studio
2. File -> Open -> select the `android` directory
3. Wait for Gradle sync to complete
4. Run -> Run 'app'

## Architecture

The app follows functional programming principles with immutable data
structures:

- **Models.kt**: Immutable data classes for state management
- **BleManager.kt**: BLE connection and CSC measurement handling using Kotlin
  Flow
- **BikeViewModel.kt**: State management with reactive updates
- **MainActivity.kt**: Jetpack Compose UI

### BLE Implementation

The app implements the standard Cycling Speed and Cadence (CSC) profile:

- Service UUID: `0x1816`
- CSC Measurement Characteristic UUID: `0x2A5B`
- Scans with `SCAN_MODE_LOW_POWER` and service UUID filter
- Subscribes to CSC notifications for real-time updates
- Parses cumulative revolutions and event timing
- Calculates instantaneous cadence from consecutive measurements

### State Management

Uses Kotlin Flow for reactive state updates:

- `BikeState`: Immutable state containing cadence, revolutions, and connection
  status
- `ConnectionState`: Sealed class representing BLE connection lifecycle
- Pure function `calculateCadence()` for cadence computation

## Permissions

Required permissions (automatically requested at runtime):

- `BLUETOOTH_SCAN`: For discovering BLE devices
- `BLUETOOTH_CONNECT`: For connecting to the bike tracker

## Usage

1. Launch the app
2. Grant Bluetooth permissions when prompted
3. Tap "Connect" to scan for and connect to your bike tracker
4. Start pedaling to see real-time cadence updates
5. Tap "Disconnect" to end the session

## Testing

The app can be tested with the ESP32 firmware in the `firmware` directory.
Ensure the firmware is running and advertising the CSC service before
connecting.

## Known Limitations

- Currently connects on app launch only (no background sync yet)
- Single device support
- No persistent data storage (Stage 3 feature)
- No HealthConnect integration (Stage 4 feature)

## Next Steps (Future Stages)

- Stage 3: Background sync with WorkManager
- Stage 4: HealthConnect integration
- Stage 5: Enhanced UI with session history and charts
