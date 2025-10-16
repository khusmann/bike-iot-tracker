# A2 HealthConnect Setup - Testing Guide

This guide walks you through testing the HealthConnect integration implemented in A2.

## Prerequisites

### Hardware/Software Requirements
- Android device or emulator with **API 34+ (Android 14)** for full testing
- API 28+ for availability check testing only
- HealthConnect app installed (pre-installed on Android 14+)
- ADB installed and device connected

### Build and Install

```bash
cd /home/khusmann/Projects/bike-iot-tracker/android
./gradlew installDebug
```

## Test 1: HealthConnect Availability Check ✓

**Goal:** Verify the app correctly detects HealthConnect availability

### Steps:
1. Install and launch the app
2. Grant Bluetooth and HealthConnect permissions when prompted
3. Look at the main screen - you should see text displaying:
   - "HealthConnect: Available" (green) on API 34+
   - "HealthConnect: Not Available" (red) on API < 28

### Verify via Logcat:
```bash
adb logcat BikeViewModel:I *:S
```

**Expected output:**
```
BikeViewModel: HealthConnect available: true
```

### Troubleshooting:
- **"Not Available" on Android 14+**: Check if HealthConnect app is installed
  ```bash
  adb shell pm list packages | grep health
  ```
  Should show: `package:com.google.android.apps.healthdata`

- **To install HealthConnect manually:**
  - Open Play Store on device
  - Search for "Health Connect"
  - Install

---

## Test 2: Permission Request Flow ✓

**Goal:** Verify all permissions are properly requested

### Steps:
1. Uninstall the app first:
   ```bash
   adb uninstall com.biketracker
   ```

2. Reinstall and launch:
   ```bash
   ./gradlew installDebug
   adb shell am start -n com.biketracker/.MainActivity
   ```

3. You should see permission request screen with **two separate buttons**:
   - "Grant Bluetooth Permissions"
   - "Grant HealthConnect Permissions"

4. Click **"Grant Bluetooth Permissions"** first:
   - You'll see Android's permission dialog for BLUETOOTH_SCAN and BLUETOOTH_CONNECT
   - Grant both permissions
   - The button will change to "✓ Bluetooth permissions granted"

5. Click **"Grant HealthConnect Permissions"**:
   - You'll be redirected to the HealthConnect permission screen
   - You'll see permissions for:
     - Read exercise data
     - Write exercise data
   - Grant both permissions
   - You'll be returned to the app

6. After both are granted, you should see the main app screen

### Verify Permissions Granted:
```bash
adb shell dumpsys package com.biketracker | grep permission
```

**Expected output should include:**
```
android.permission.BLUETOOTH_SCAN: granted=true
android.permission.BLUETOOTH_CONNECT: granted=true
android.permission.health.READ_EXERCISE: granted=true
android.permission.health.WRITE_EXERCISE: granted=true
```

---

## Test 3: Query Last Synced Timestamp (Empty State) ✓

**Goal:** Verify querying works when no sessions exist

### Steps:
1. Ensure HealthConnect has no cycling data:
   - Open HealthConnect app on device
   - Go to Settings → Delete all data (if needed)
   - Or Settings → Manage data → Exercise → Delete cycling sessions

2. In Bike Tracker app, click **"Test HealthConnect Query"** button

3. Monitor logcat:
   ```bash
   adb logcat BikeViewModel:I HealthConnectHelper:I *:S
   ```

**Expected output:**
```
HealthConnectHelper: No previous sessions found for bike AA:BB:CC:DD:EE:FF
BikeViewModel: Last synced timestamp for bike AA:BB:CC:DD:EE:FF: 0
```

**Result:** Query returns `0` (no previous sessions)

---

## Test 4: Query Last Synced Timestamp (With Data) ✓

**Goal:** Verify querying finds existing sessions

### Setup: Add Test Data to HealthConnect

We need to manually insert test data since A3 (write implementation) isn't complete yet.

**Option A: Use a compatible fitness app**
1. Install Google Fit or Samsung Health
2. Add a manual cycling workout with start time, duration
3. Ensure it syncs to HealthConnect

**Option B: Use HealthConnect test app (if available)**
- Some Android emulators include a HealthConnect test data generator

**Option C: Wait for A3 implementation** (recommended)
- Once A3 is complete, we can write real session data and test this properly
- For now, Test 3 (empty state) validates the query logic works

### Steps (once test data exists):
1. Verify data exists in HealthConnect app:
   - Open HealthConnect
   - Browse data → Exercise → Should see cycling sessions

2. In Bike Tracker app, click **"Test HealthConnect Query"** button

3. Monitor logcat:
   ```bash
   adb logcat BikeViewModel:I HealthConnectHelper:I *:S
   ```

**Expected output (example):**
```
HealthConnectHelper: Last synced session for bike AA:BB:CC:DD:EE:FF: 1728849600
BikeViewModel: Last synced timestamp for bike AA:BB:CC:DD:EE:FF: 1728849600
```

**Note:** The timestamp will be the start time of the most recent cycling session

---

## Test 5: Multi-Bike Identification

**Goal:** Verify different bike addresses are tracked independently

This test is best performed after A3 implementation when we can write sessions with specific bike addresses.

### Manual Test (via code inspection):
1. Check [HealthConnectHelper.kt](../android/app/src/main/java/com/biketracker/HealthConnectHelper.kt):95-100
2. Confirm `clientRecordId` filter uses prefix: `"bike-${bikeAddress}-"`
3. Verify each bike address will create separate session IDs

**To test with real data (requires A3):**
1. Connect to bike with address `AA:BB:CC:DD:EE:FF`, sync sessions
2. Connect to bike with address `11:22:33:44:55:66`, sync sessions
3. Query both addresses separately
4. Verify each returns different timestamps

---

## Test 6: API Level Compatibility

**Goal:** Verify graceful handling on older Android versions

### Test on API 28-33 (Android 9-13):
```bash
# Use an emulator or device with API 28-33
adb logcat BikeViewModel:I HealthConnectHelper:I *:S
```

**Expected:**
- App launches successfully
- Shows "HealthConnect: Not Available" (depending on device/API)
- No crashes or errors
- HealthConnect permissions not requested on API < 34

### Test on API < 28 (Android 8.1 and earlier):
**Expected:**
- App shows "HealthConnect: Not Available"
- Logcat: `HealthConnect not available: requires API 28+`

---

## Common Issues & Solutions

### Issue: HealthConnect shows as unavailable on Android 14
**Solution:**
- Check HealthConnect app is installed: `adb shell pm list packages | grep health`
- Update HealthConnect app from Play Store
- Reboot device

### Issue: Permissions not requested
**Solution:**
- Verify API level >= 34 for health permissions
- Check [AndroidManifest.xml](../android/app/src/main/AndroidManifest.xml) has health permissions
- Uninstall and reinstall app

### Issue: Query always returns 0
**Expected behavior until A3 is complete:**
- No sessions have been written yet
- 0 is correct return value

### Issue: Query throws SecurityException
**Solution:**
- Health permissions not granted
- Check: `adb shell dumpsys package com.biketracker | grep health`
- Reinstall and grant permissions

---

## Success Criteria

- ✅ **A2.1**: HealthConnect dependency added (builds successfully)
- ✅ **A2.2**: Health permissions requested on API 34+ (intent filter required!)
- ✅ **A2.3**: Availability check works correctly across API levels
- ✅ **A2.4**: Query returns 0 when no sessions exist (correct behavior - VERIFIED)
- ⏳ **A2.4 (full test)**: Query returns correct timestamp (requires A3 data)

---

## Status: ✅ A2 COMPLETE

All HealthConnect setup tasks completed successfully. The critical fix was adding the intent filter to AndroidManifest.xml:

```xml
<intent-filter>
    <action android:name="android.intent.action.VIEW_PERMISSION_USAGE"/>
    <category android:name="android.intent.category.HEALTH_PERMISSIONS"/>
</intent-filter>
```

Without this intent filter, the permission request contract fails silently.

**Test Results:**
- HealthConnect availability detection: ✅ Working
- Permission request flow: ✅ Working (opens HealthConnect permission dialog)
- Permission checking: ✅ Working
- Query last synced timestamp: ✅ Working (returns 0 when no data exists)

---

## Next Steps

After completing these tests, you're ready to proceed to:
- **A3: Sync Implementation** - Write sessions to HealthConnect
- Then return to **Test 4** to verify full query functionality with real data

---

## Quick Test Commands Reference

```bash
# Install app
./gradlew installDebug

# Launch app
adb shell am start -n com.biketracker/.MainActivity

# Monitor logs
adb logcat BikeViewModel:I HealthConnectHelper:I *:S

# Check permissions
adb shell dumpsys package com.biketracker | grep -E "(permission|health)"

# Uninstall
adb uninstall com.biketracker

# Check HealthConnect installed
adb shell pm list packages | grep health
```
