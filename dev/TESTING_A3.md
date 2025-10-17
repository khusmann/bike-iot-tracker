# A3 Sync Implementation Testing Guide

## Quick Test (5 minutes)

### 1. Prepare Test Data
```bash
# Create a test session on the bike
# - Pedal for 30 seconds
# - Stop and wait 10 minutes for session to close
# OR manually create via WebREPL
```

### 2. Monitor Sync
```bash
# Terminal 1: Watch logs
adb logcat BikeSync:V *:S

# Terminal 2: Trigger sync (one of these methods)
# Method A: Restart app to trigger WorkManager
adb shell am force-stop com.biketracker && adb shell am start -n com.biketracker/.MainActivity

# Method B: Wait for scheduled sync (default interval)
# (Check SyncScheduler.kt for current interval)
```

### 3. Verify Success
Look for this log sequence:
```
D/BikeSync: Background sync worker started
D/BikeSync: BLE scan started
D/BikeSync: Device discovered: BikeTracker
D/BikeSync: Found bike tracker: BikeTracker
D/BikeSync: Last synced timestamp: 0
D/BikeSync: Connected to GATT server
D/BikeSync: MTU changed to: 512
D/BikeSync: Discovering services...
D/BikeSync: Services discovered
D/BikeSync: Received response: {"session": {...}, "remaining_sessions": 0}
D/BikeSync: Session: start=1697500000, end=1697501800, revolutions=456, remaining=0
D/BikeSync: Successfully wrote session to HealthConnect: 1697500000
D/BikeSync: Sync complete - no more sessions
D/BikeSync: Background sync completed successfully
```

## Detailed Test Cases

### Test 1: First Sync (No Previous Data)

**Setup:**
- Clean HealthConnect data (or use fresh device)
- Create 1-3 sessions on bike

**Expected:**
- `Last synced timestamp: 0`
- All sessions synced
- `clientRecordId` format: `bike-{MAC}-{timestamp}`

**Verify:**
```bash
# Check logs show all sessions
adb logcat BikeSync:V *:S | grep "Successfully wrote session"

# Count should match number of sessions created
```

### Test 2: Incremental Sync

**Setup:**
- Sync once (establishes last timestamp)
- Create new session on bike
- Sync again

**Expected:**
- `Last synced timestamp: <previous session timestamp>`
- Only new session synced
- `remaining_sessions` counts down correctly

**Verify:**
```bash
# First sync should show older timestamp
# Second sync should only sync new session
```

### Test 3: MTU Negotiation

**Expected:**
- MTU negotiated to 512 (or device max)
- If MTU < 185: sync aborts with error

**Verify:**
```bash
# Look for:
D/BikeSync: MTU changed to: <value>
# If <value> >= 185: continues
# If <value> < 185: shows error and disconnects
```

### Test 4: Connection Errors

**Test scenarios:**
- Bike out of range
- Bluetooth disabled during sync
- Bike firmware crashes mid-sync

**Expected:**
- Graceful failure and retry
- Partial progress saved to HealthConnect
- Next sync resumes from last written session

**Verify:**
```bash
# Look for retry behavior:
W/BikeSync: Background sync failed, will retry
# OR
W/BikeSync: Background sync timed out after 30000ms
```

### Test 5: Empty Session List

**Setup:**
- Sync all sessions (so last timestamp is current)
- Don't create new sessions
- Sync again

**Expected:**
- Response: `{"session": null, "remaining_sessions": 0}`
- Log: "Sync complete - no more sessions"
- Returns success (not retry)

### Test 6: Multiple Sessions

**Setup:**
- Create 5+ sessions on bike
- Clear HealthConnect
- Sync

**Expected:**
- Loops through all sessions
- `remaining_sessions` decrements: 4 → 3 → 2 → 1 → 0
- All sessions written to HealthConnect

**Verify:**
```bash
# Count "Successfully wrote session" log lines
adb logcat BikeSync:V *:S | grep "Successfully wrote session" | wc -l
```

### Test 7: Timeout Handling

**Setup:**
- Bike firmware responding very slowly
- Or simulate by adding delays

**Expected:**
- Sync aborts after 30 seconds
- Returns retry status
- Next sync resumes from last written session

**Verify:**
```bash
# Look for:
W/BikeSync: Background sync timed out after 30000ms
```

### Test 8: Background Sync While App Closed

**Setup:**
- Close app (swipe away from recent apps)
- Wait for WorkManager schedule

**Expected:**
- Sync runs in background
- Logs appear in logcat
- No UI required

**Verify:**
```bash
# Monitor logs while app is closed
adb logcat BikeSync:V WorkManager:V *:S
```

## Debugging Tips

### Problem: No "Background sync worker started" log
**Solutions:**
- Check WorkManager schedule in `SyncScheduler.kt`
- Manually trigger with broadcast intent
- Check battery optimization settings

### Problem: "BLE scan did not find bike tracker"
**Solutions:**
- Verify bike firmware is running: `BikeTracker` advertised
- Check Bluetooth is enabled on phone
- Reduce distance between devices
- Check scan filters in `scanForDevice()`

### Problem: "Sync service not found"
**Solutions:**
- Verify firmware has Sync Service UUID: `0x0000FF00-...`
- Check firmware is running Stage 3 code with F3 refactor
- Use `firmware/test_ble_client.py --sync` to verify service exists

### Problem: "MTU too small"
**Solutions:**
- This is device-specific (some phones have low MTU limits)
- Most modern phones support 512 MTU
- Consider chunking responses if this is common (future work)

### Problem: Sessions not appearing in HealthConnect
**Solutions:**
- Check HealthConnect permissions granted
- Verify `clientRecordId` format: `bike-{MAC}-{timestamp}`
- Check for exceptions in "Failed to write session" logs
- Verify timestamps are valid Unix epoch seconds

### Problem: Parse errors
**Solutions:**
- Check firmware JSON response format matches:
  ```json
  {"session": {"start_time": 123, "end_time": 456, "revolutions": 789}, "remaining_sessions": 2}
  ```
- Verify characteristic read returns correct data
- Check MTU is sufficient for JSON response

## Integration with Firmware Test Client

Use the existing firmware test client to verify sessions:

```bash
cd /home/khusmann/Projects/bike-iot-tracker/firmware

# Activate venv
source .venv/bin/activate

# Install bleak if needed
pip install bleak

# Test sync protocol
python test_ble_client.py --sync

# Expected output:
# Scanning for 'BikeTracker'...
# Found BikeTracker at XX:XX:XX:XX:XX:XX
# Connecting to XX:XX:XX:XX:XX:XX...
# Connected: True
# Last synced timestamp: 0
# Session 1: {...}
# Session 2: {...}
# ...
# Sync complete
```

This verifies the firmware side is working correctly before testing Android integration.

## Success Criteria

✅ Sync completes within 30 seconds
✅ All sessions synced to HealthConnect
✅ Correct `clientRecordId` format used
✅ MTU negotiation succeeds (or fails gracefully)
✅ Incremental sync works (only new sessions)
✅ Connection errors handled gracefully
✅ Background sync works with app closed
✅ No GATT errors or crashes

## Next Steps After Testing

Once A3 is verified:
- [ ] Implement A4: UI updates to show sync status
- [ ] Run A1 full test suite (background worker tests)
- [ ] Test battery usage over 24 hours
- [ ] Multi-client testing (sync from multiple phones)
