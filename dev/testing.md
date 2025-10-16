# A1 Background Sync Testing Guide

This guide walks you through testing the A1 Background Sync Infrastructure implementation.

## Prerequisites

1. **ESP32 bike tracker** must be running and advertising BLE services
2. **Android device** with:
   - Bluetooth enabled
   - Developer options enabled
   - USB debugging enabled
   - Connected to development computer via USB
3. **ADB installed** on your development computer

## Quick Setup

### Enable Developer Options on Android

If you haven't already:

1. Go to **Settings > About Phone**
2. Tap **Build Number** 7 times
3. Go back to **Settings > System > Developer Options**
4. Enable **USB Debugging**

### Verify ADB Connection

```bash
adb devices
```

You should see your device listed. If prompted on the phone, allow USB debugging.

### Build and Install the App

```bash
cd android
./gradlew installDebug
```

## Testing Checklist

### A1.T1: Test WorkManager Triggers Background Worker

**Goal:** Verify that WorkManager successfully schedules and runs the background sync worker.

**Steps:**

1. **Install and launch the app:**
   ```bash
   ./gradlew installDebug
   adb shell am start -n com.biketracker/.MainActivity
   ```

2. **Start monitoring logs:**
   ```bash
   adb logcat BikeSync:V *:S
   ```

3. **Grant Bluetooth permissions** if prompted in the app

4. **Wait for the first sync** (up to 15 minutes)
   - Or force immediate execution (see "Trigger Manual Sync" below)

5. **Expected output in logcat:**
   ```
   BikeSync: Background sync worker started
   BikeSync: Periodic background sync scheduled (every 15 minutes)
   ```

**Trigger Manual Sync (Optional):**

To test immediately without waiting 15 minutes, you can force the worker to run:

```bash
adb shell am broadcast -a androidx.work.diagnostics.REQUEST_DIAGNOSTICS -n com.biketracker/androidx.work.impl.diagnostics.DiagnosticsReceiver
```

Or use the WorkManager testing library (requires adding test dependency).

**Pass Criteria:**
- "Background sync worker started" appears in logs
- Message appears on schedule (every 15 minutes after first trigger)

---

### A1.T2: Test Low-Power BLE Scanning Finds Bike

**Goal:** Verify that low-power BLE scanning successfully discovers the bike tracker.

**Prerequisites:**
- ESP32 bike tracker is powered on and advertising

**Steps:**

1. **Monitor logs with both app and Bluetooth:**
   ```bash
   adb logcat BikeSync:V BluetoothAdapter:V *:S
   ```

2. **Trigger sync** (manually or wait for scheduled sync)

3. **Expected output in logcat:**
   ```
   BikeSync: Background sync worker started
   BikeSync: BLE scan started
   BikeSync: Device discovered: BikeTracker
   BikeSync: Found bike tracker: BikeTracker
   BikeSync: Background sync completed successfully
   ```

4. **Note the time between "scan started" and "device discovered"**

**Pass Criteria:**
- Device name "BikeTracker" appears in logs
- Scan completes within 10 seconds
- No scan errors

**Troubleshooting:**
- If device not found, verify ESP32 is advertising with name "BikeTracker"
- Check ESP32 firmware is running: `screen /dev/ttyUSB0 115200` (or your device)
- Verify CSC Service UUID (0x1816) is being advertised

---

### A1.T3: Test Background Connection Lifecycle

**Goal:** Verify the complete connection lifecycle completes within 30 seconds.

**Steps:**

1. **Monitor logs:**
   ```bash
   adb logcat BikeSync:V *:S
   ```

2. **Trigger sync and measure duration**

3. **Expected output:**
   ```
   BikeSync: Background sync worker started
   BikeSync: BLE scan started
   BikeSync: Device discovered: BikeTracker
   BikeSync: Found bike tracker: BikeTracker
   BikeSync: Background sync completed successfully
   ```

4. **Calculate time from "worker started" to "completed successfully"**

**Pass Criteria:**
- Complete sync cycle under 30 seconds
- No GATT connection errors
- "completed successfully" message appears

**Note:** Currently the worker only scans and doesn't connect yet. Full connection will be implemented in A3. This test verifies the scanning phase completes quickly.

---

### A1.T4: Test App Killed/Closed Scenarios

**Goal:** Verify background sync continues to work even when the app is closed.

**Steps:**

1. **Launch app and grant permissions**

2. **Close app completely:**
   - Open Recent Apps (square button or swipe up gesture)
   - Swipe away the Bike Tracker app

3. **Start monitoring logs:**
   ```bash
   adb logcat BikeSync:V WorkManager:V *:S
   ```

4. **Wait 15 minutes** (or until next scheduled sync)

5. **Expected output:**
   ```
   WorkManager: Worker started for ...BackgroundSyncWorker
   BikeSync: Background sync worker started
   BikeSync: BLE scan started
   BikeSync: Device discovered: BikeTracker
   BikeSync: Background sync completed successfully
   ```

**Pass Criteria:**
- "Background sync worker started" appears even with app closed
- Sync completes successfully
- WorkManager logs show worker execution

---

### A1.T5: Test Device Reboot

**Goal:** Verify background sync resumes after device reboot.

**Steps:**

1. **Check current sync status before reboot:**
   ```bash
   adb logcat BikeSync:V *:S
   ```
   Note the last sync time or count if visible.

2. **Reboot the phone:**
   ```bash
   adb reboot
   ```

3. **Wait for phone to fully boot** (1-2 minutes)

4. **Reconnect ADB and monitor logs:**
   ```bash
   adb logcat BikeSync:V WorkManager:V *:S
   ```

5. **Wait up to 15 minutes** for the first post-reboot sync

6. **Expected output:**
   ```
   BikeSync: Periodic background sync scheduled (every 15 minutes)
   ...
   BikeSync: Background sync worker started
   ```

**Pass Criteria:**
- Background sync resumes after reboot
- First sync occurs within 15 minutes of boot
- No errors in WorkManager initialization

**Note:** WorkManager automatically reschedules work after device reboot.

---

### A1.T6: Verify Foreground Connection Still Works

**Goal:** Ensure the existing foreground CSC connection isn't broken by background sync.

**Steps:**

1. **Launch the app**

2. **Monitor logs:**
   ```bash
   adb logcat BikeSync:V BleManager:V *:S
   ```

3. **Tap "Connect" in the app**

4. **Expected output:**
   ```
   BleManager: Starting BLE scan
   BleManager: Found device: BikeTracker
   BleManager: Connected to GATT server
   BleManager: Requesting CSC notifications
   BleManager: CSC notifications enabled successfully
   BleManager: CSC measurement received: 5 bytes
   ```

5. **Verify the app shows:**
   - Connection status: "Connected: BikeTracker"
   - Live cadence updates as you pedal
   - Total revolutions counter

6. **While foreground connection is active, trigger background sync:**
   ```bash
   # This will test if both can coexist
   adb shell am broadcast -a androidx.work.diagnostics.REQUEST_DIAGNOSTICS -n com.biketracker/androidx.work.impl.diagnostics.DiagnosticsReceiver
   ```

7. **Check for errors:**
   - No "GATT connection busy" errors
   - No "connection conflict" errors
   - Foreground connection remains stable

**Pass Criteria:**
- Foreground connection works as before
- No conflicts when background sync runs
- CSC data continues to update in the app

---

## Additional Verification

### Check WorkManager Job Status

You can inspect the current WorkManager jobs:

```bash
adb shell dumpsys jobscheduler | grep com.biketracker
```

This shows scheduled jobs for the app.

### Check App Battery Usage

After 24 hours of testing:

```bash
adb shell dumpsys batterystats com.biketracker
```

Look for battery usage statistics. Target is < 2% per day.

### Manual Worker Cancellation (For Testing)

To cancel the background sync (useful for testing scheduling):

Add a button in the app that calls:
```kotlin
SyncScheduler.cancelSync(applicationContext)
```

Then reschedule:
```kotlin
SyncScheduler.schedulePeriodicSync(applicationContext)
```

---

## Common Issues

### Issue: No logs appearing

**Solution:**
- Verify adb connection: `adb devices`
- Check log tag is correct: `BikeSync`
- Try without filter: `adb logcat | grep BikeSync`

### Issue: Worker not running after 15 minutes

**Solution:**
- Android may delay background work for battery optimization
- Disable battery optimization for the app:
  - Settings > Apps > Bike Tracker > Battery > Unrestricted
- Or use Doze testing commands:
  ```bash
  adb shell dumpsys battery unplug
  adb shell dumpsys deviceidle step
  ```

### Issue: Bluetooth permissions denied

**Solution:**
- Grant permissions manually in Settings > Apps > Bike Tracker > Permissions
- Or reinstall the app and grant when prompted

### Issue: Device not found during scan

**Solution:**
- Verify ESP32 is powered and running
- Check ESP32 logs via serial connection
- Ensure BLE advertising is active
- Try manual BLE scan with nRF Connect app to verify device is visible

---

## Next Steps

After completing these tests:

1. **Mark A1 tasks as complete** in [tasks.md](../dev/tasks.md)
2. **Proceed to A2**: Local Database implementation
3. **Then A3**: Full sync protocol implementation (actual data transfer)

The current implementation verifies the background infrastructure works. The actual session data sync will be added in A3 when connecting to the Sync Service (0xFF00).

---

## Quick Reference

### Useful ADB Commands

```bash
# View logs
adb logcat BikeSync:V *:S

# Clear logs
adb logcat -c

# Install app
cd android && ./gradlew installDebug

# Launch app
adb shell am start -n com.biketracker/.MainActivity

# Force stop app
adb shell am force-stop com.biketracker

# Reboot device
adb reboot

# Check battery stats
adb shell dumpsys batterystats com.biketracker

# Check scheduled jobs
adb shell dumpsys jobscheduler | grep com.biketracker
```

### Log Tags to Monitor

- `BikeSync` - Background sync worker
- `BleManager` - Foreground BLE connection
- `WorkManager` - Worker scheduling and execution
- `BluetoothAdapter` - System Bluetooth events
