package com.biketracker

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.os.ParcelUuid
import android.util.Log
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.health.connect.client.records.metadata.Metadata
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull
import org.json.JSONObject
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.time.Instant
import java.time.ZoneOffset
import java.util.UUID
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/**
 * Background worker for syncing bike tracker data
 *
 * Runs periodically to:
 * 1. Scan for bike tracker with low power mode
 * 2. Connect briefly (under 30 seconds)
 * 3. Sync any new session data
 * 4. Disconnect and complete
 *
 * Designed to minimize battery usage through:
 * - SCAN_MODE_LOW_POWER with device/service filters
 * - Short connection duration (< 30 seconds)
 * - No persistent foreground service
 */
class BackgroundSyncWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    companion object {
        const val TAG = "BikeSync"
        const val WORK_NAME = "background_sync"

        // Sync Service UUID (from firmware Stage 3)
        private val SYNC_SERVICE_UUID = UUID.fromString("0000FF00-0000-1000-8000-00805f9b34fb")

        // CSC Service UUID (for scanning compatibility)
        private val CSC_SERVICE_UUID = UUID.fromString("00001816-0000-1000-8000-00805f9b34fb")

        // Accept both "BikeTracker" (firmware running) and "MPY ESP32" (firmware not started yet)
        private val ACCEPTED_DEVICE_NAMES = setOf("BikeTracker", "MPY ESP32")

        // Timeouts
        private const val SCAN_TIMEOUT_MS = 10_000L
        private const val TOTAL_TIMEOUT_MS = 30_000L
    }

    override suspend fun doWork(): Result {
        Log.d(TAG, "Background sync worker started")
        val syncPrefs = SyncPreferences(applicationContext)

        // Record sync attempt
        syncPrefs.lastSyncAttemptTimestamp = System.currentTimeMillis()

        return try {
            // Run entire sync with 30 second timeout
            val syncResult = withTimeoutOrNull(TOTAL_TIMEOUT_MS) {
                performSync()
            }

            when {
                syncResult == true -> {
                    Log.d(TAG, "Background sync completed successfully")
                    Result.success()
                }
                syncResult == false -> {
                    Log.w(TAG, "Background sync failed, will retry")
                    syncPrefs.recordSyncFailure("Sync failed (device not found or connection error)")
                    Result.retry()
                }
                else -> {
                    Log.w(TAG, "Background sync timed out after ${TOTAL_TIMEOUT_MS}ms")
                    syncPrefs.recordSyncFailure("Sync timed out after ${TOTAL_TIMEOUT_MS}ms")
                    Result.retry()
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Background sync error: ${e.message}", e)
            syncPrefs.recordSyncFailure("Error: ${e.message}")
            Result.failure()
        }
    }

    /**
     * Performs the full sync operation
     * @return true if successful, false if should retry
     */
    @SuppressLint("MissingPermission")
    private suspend fun performSync(): Boolean {
        val device = scanForDevice() ?: run {
            Log.w(TAG, "BLE scan did not find bike tracker")
            return false
        }

        Log.d(TAG, "Found bike tracker: ${device.device.name}")

        // Get last synced timestamp from SharedPreferences
        // Note: We use SharedPreferences instead of querying HealthConnect because
        // HealthConnect restricts background read access (privacy feature). While
        // Android 15+ offers READ_HEALTH_DATA_IN_BACKGROUND permission, using
        // SharedPreferences works on all Android versions without extra permissions.
        val syncPrefs = SyncPreferences(applicationContext)
        val lastSyncedTimestamp = syncPrefs.lastSyncedSessionTimestamp
        Log.d(TAG, "Last synced session timestamp from preferences: $lastSyncedTimestamp")

        // Connect to device and sync
        var gatt: BluetoothGatt? = null
        try {
            val syncResult = suspendCancellableCoroutine<Boolean> { continuation ->
                var resumed = false
                var sessionsSynced = 0

                gatt = device.device.connectGatt(
                    applicationContext,
                    false,
                    object : BluetoothGattCallback() {
                        private var mtuNegotiated = false
                        private var servicesDiscovered = false
                        private var sessionDataChar: BluetoothGattCharacteristic? = null
                        private var currentOperation: SyncOperation? = null
                        private var currentLastSyncedTimestamp = lastSyncedTimestamp

                        override fun onConnectionStateChange(
                            gatt: BluetoothGatt,
                            status: Int,
                            newState: Int
                        ) {
                            when (newState) {
                                BluetoothProfile.STATE_CONNECTED -> {
                                    Log.d(TAG, "Connected to GATT server")
                                    // A3.1: Request MTU negotiation
                                    val mtuRequested = gatt.requestMtu(512)
                                    if (!mtuRequested) {
                                        Log.e(TAG, "Failed to request MTU")
                                        resumeOnce(continuation, false)
                                    }
                                }
                                BluetoothProfile.STATE_DISCONNECTED -> {
                                    Log.d(TAG, "Disconnected from GATT server")
                                    gatt.close()
                                    // Only resume if we haven't already
                                    if (!resumed) {
                                        resumed = true
                                        continuation.resume(false)
                                    }
                                }
                            }
                        }

                        override fun onMtuChanged(gatt: BluetoothGatt, mtu: Int, status: Int) {
                            if (status == BluetoothGatt.GATT_SUCCESS) {
                                Log.d(TAG, "MTU changed to: $mtu")

                                // A3.1: Verify MTU is sufficient (>= 185 bytes)
                                if (mtu < 185) {
                                    Log.e(TAG, "MTU too small: $mtu < 185, aborting sync")
                                    gatt.disconnect()
                                    resumeOnce(continuation, false)
                                    return
                                }

                                mtuNegotiated = true

                                // Start service discovery
                                Log.d(TAG, "Discovering services...")
                                val discovered = gatt.discoverServices()
                                if (!discovered) {
                                    Log.e(TAG, "Failed to start service discovery")
                                    gatt.disconnect()
                                    resumeOnce(continuation, false)
                                }
                            } else {
                                Log.e(TAG, "MTU change failed with status: $status")
                                gatt.disconnect()
                                resumeOnce(continuation, false)
                            }
                        }

                        override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
                            if (status == BluetoothGatt.GATT_SUCCESS) {
                                Log.d(TAG, "Services discovered")

                                // A3.3: Find sync service and session data characteristic
                                val syncService = gatt.getService(SYNC_SERVICE_UUID)
                                if (syncService == null) {
                                    Log.e(TAG, "Sync service not found")
                                    gatt.disconnect()
                                    resumeOnce(continuation, false)
                                    return
                                }

                                // UUID 0xFF01 as defined in firmware/src/sync_service.py
                                val sessionDataUuid = UUID.fromString("0000FF01-0000-1000-8000-00805f9b34fb")
                                sessionDataChar = syncService.getCharacteristic(sessionDataUuid)

                                if (sessionDataChar == null) {
                                    Log.e(TAG, "Session data characteristic not found")
                                    gatt.disconnect()
                                    resumeOnce(continuation, false)
                                    return
                                }

                                servicesDiscovered = true

                                // A3.4: Start sync loop
                                requestNextSession(gatt, sessionDataChar!!)
                            } else {
                                Log.e(TAG, "Service discovery failed with status: $status")
                                gatt.disconnect()
                                resumeOnce(continuation, false)
                            }
                        }

                        override fun onCharacteristicWrite(
                            gatt: BluetoothGatt,
                            characteristic: BluetoothGattCharacteristic,
                            status: Int
                        ) {
                            if (status != BluetoothGatt.GATT_SUCCESS) {
                                Log.e(TAG, "Characteristic write failed with status: $status")
                                gatt.disconnect()
                                resumeOnce(continuation, false)
                                return
                            }

                            // Add delay to allow ESP32 to update characteristic value
                            // The ESP32 needs time to process the write and update the value
                            Thread.sleep(500)

                            // After write succeeds, read the response
                            val readSuccess = gatt.readCharacteristic(characteristic)
                            if (!readSuccess) {
                                Log.e(TAG, "Failed to initiate characteristic read")
                                gatt.disconnect()
                                resumeOnce(continuation, false)
                            }
                        }

                        override fun onCharacteristicRead(
                            gatt: BluetoothGatt,
                            characteristic: BluetoothGattCharacteristic,
                            value: ByteArray,
                            status: Int
                        ) {
                            if (status != BluetoothGatt.GATT_SUCCESS) {
                                Log.e(TAG, "Characteristic read failed with status: $status")
                                gatt.disconnect()
                                resumeOnce(continuation, false)
                                return
                            }

                            try {
                                // Parse JSON response
                                val jsonStr = String(value)
                                Log.d(TAG, "Received response: $jsonStr")

                                val jsonObj = JSONObject(jsonStr)
                                val sessionJson = jsonObj.optJSONObject("session")
                                val remainingSessions = jsonObj.getInt("remaining_sessions")

                                if (sessionJson == null) {
                                    // A3.4: No more sessions, sync complete
                                    Log.d(TAG, "Sync complete - $sessionsSynced sessions synced")

                                    // Record successful sync (even if 0 sessions - still a successful connection)
                                    syncPrefs.recordSyncSuccess(device.device.address)
                                    Log.d(TAG, "Recorded successful sync to local storage")

                                    // Update last session data update timestamp if we synced any sessions
                                    if (sessionsSynced > 0) {
                                        syncPrefs.lastSessionDataUpdateTimestamp = System.currentTimeMillis()
                                        Log.d(TAG, "Updated last session data update timestamp")
                                    }

                                    gatt.disconnect()
                                    resumeOnce(continuation, true)
                                    return
                                }

                                // A3.5: Convert session to HealthConnect format and write
                                val startTime = sessionJson.getLong("start_time")
                                val endTime = sessionJson.getLong("end_time")
                                val revolutions = sessionJson.getInt("revolutions")

                                Log.d(TAG, "Session: start=$startTime, end=$endTime, revolutions=$revolutions, remaining=$remainingSessions")

                                // Write to HealthConnect
                                CoroutineScope(Dispatchers.IO).launch {
                                    try {
                                        writeSessionToHealthConnect(
                                            device.device.address,
                                            startTime,
                                            endTime,
                                            revolutions
                                        )

                                        // Update last synced timestamp and increment counter
                                        currentLastSyncedTimestamp = startTime
                                        sessionsSynced++

                                        // Update the last synced session timestamp in preferences
                                        syncPrefs.lastSyncedSessionTimestamp = startTime

                                        // Request next session
                                        requestNextSession(gatt, sessionDataChar!!)
                                    } catch (e: Exception) {
                                        // A3.6: Handle HealthConnect write errors
                                        Log.e(TAG, "Error writing session to HealthConnect: ${e.message}", e)
                                        // Continue to next session despite error
                                        requestNextSession(gatt, sessionDataChar!!)
                                    }
                                }
                            } catch (e: Exception) {
                                // A3.6: Handle parse errors
                                Log.e(TAG, "Error parsing session response: ${e.message}", e)
                                gatt.disconnect()
                                resumeOnce(continuation, false)
                            }
                        }

                        private fun requestNextSession(
                            gatt: BluetoothGatt,
                            characteristic: BluetoothGattCharacteristic
                        ) {
                            // A3.4: Write lastSyncedTimestamp as uint32 little-endian
                            val buffer = ByteBuffer.allocate(4)
                            buffer.order(ByteOrder.LITTLE_ENDIAN)
                            buffer.putInt(currentLastSyncedTimestamp.toInt())

                            characteristic.value = buffer.array()
                            characteristic.writeType = BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT

                            val writeSuccess = gatt.writeCharacteristic(characteristic)
                            if (!writeSuccess) {
                                Log.e(TAG, "Failed to write characteristic")
                                gatt.disconnect()
                                resumeOnce(continuation, false)
                            }
                        }

                        private fun resumeOnce(
                            cont: kotlin.coroutines.Continuation<Boolean>,
                            value: Boolean
                        ) {
                            if (!resumed) {
                                resumed = true
                                cont.resume(value)
                            }
                        }
                    },
                    BluetoothDevice.TRANSPORT_LE
                )
            }

            return syncResult
        } catch (e: Exception) {
            Log.e(TAG, "Sync error: ${e.message}", e)
            gatt?.close()
            return false
        }
    }

    /**
     * A3.5: Write a session to HealthConnect
     */
    private suspend fun writeSessionToHealthConnect(
        bikeAddress: String,
        startTime: Long,
        endTime: Long,
        @Suppress("UNUSED_PARAMETER") revolutions: Int  // Reserved for future cadence time series
    ) {
        val healthConnectClient = HealthConnectClient.getOrCreate(applicationContext)

        val exerciseSession = ExerciseSessionRecord(
            startTime = Instant.ofEpochSecond(startTime),
            startZoneOffset = null,
            endTime = Instant.ofEpochSecond(endTime),
            endZoneOffset = null,
            exerciseType = ExerciseSessionRecord.EXERCISE_TYPE_BIKING_STATIONARY,
            title = "Stationary Bike",
            metadata = Metadata(
                clientRecordId = "bike-$bikeAddress-$startTime"
            )
        )

        try {
            healthConnectClient.insertRecords(listOf(exerciseSession))
            Log.d(TAG, "Successfully wrote session to HealthConnect: $startTime")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to write session to HealthConnect", e)
            throw e
        }
    }

    /**
     * Internal helper for sync operations
     */
    private enum class SyncOperation {
        REQUESTING_SESSION,
        READING_SESSION
    }

    /**
     * Scans for bike tracker device with low power settings
     * @return ScanResult if device found, null otherwise
     */
    @SuppressLint("MissingPermission")
    private suspend fun scanForDevice(): ScanResult? {
        val bluetoothManager = applicationContext.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
        val adapter = bluetoothManager?.adapter

        if (adapter == null || !adapter.isEnabled) {
            Log.w(TAG, "Bluetooth not available or disabled")
            return null
        }

        val scanner = adapter.bluetoothLeScanner ?: run {
            Log.w(TAG, "BLE scanner not available")
            return null
        }

        return suspendCancellableCoroutine { continuation ->
            var resumed = false

            val callback = object : ScanCallback() {
                override fun onScanResult(callbackType: Int, result: ScanResult) {
                    Log.d(TAG, "Device discovered: ${result.device.name ?: "unknown"}")

                    if (!resumed && result.device.name in ACCEPTED_DEVICE_NAMES) {
                        resumed = true
                        scanner.stopScan(this)
                        continuation.resume(result)
                    }
                }

                override fun onScanFailed(errorCode: Int) {
                    Log.e(TAG, "BLE scan failed with error: $errorCode")
                    if (!resumed) {
                        resumed = true
                        scanner.stopScan(this)
                        continuation.resume(null)
                    }
                }
            }

            // Configure low-power scanning with filters
            val scanFilter = ScanFilter.Builder()
                .setServiceUuid(ParcelUuid(CSC_SERVICE_UUID))
                .build()

            val scanSettings = ScanSettings.Builder()
                .setScanMode(ScanSettings.SCAN_MODE_LOW_POWER)
                .build()

            Log.d(TAG, "BLE scan started")
            scanner.startScan(listOf(scanFilter), scanSettings, callback)

            // Setup cancellation
            continuation.invokeOnCancellation {
                Log.d(TAG, "BLE scan cancelled")
                scanner.stopScan(callback)
            }

            // Schedule timeout
            CoroutineScope(Dispatchers.IO).launch {
                delay(SCAN_TIMEOUT_MS)
                if (!resumed) {
                    Log.d(TAG, "BLE scan stopped (timeout)")
                    resumed = true
                    scanner.stopScan(callback)
                    continuation.resume(null)
                }
            }
        }
    }
}
