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

        private const val DEVICE_NAME_PREFIX = "BikeTracker"

        // Timeouts
        private const val SCAN_TIMEOUT_MS = 10_000L
        private const val TOTAL_TIMEOUT_MS = 30_000L
    }

    override suspend fun doWork(): Result {
        Log.d(TAG, "Background sync worker started")

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
                    Result.retry()
                }
                else -> {
                    Log.w(TAG, "Background sync timed out after ${TOTAL_TIMEOUT_MS}ms")
                    Result.retry()
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Background sync error: ${e.message}", e)
            Result.failure()
        }
    }

    /**
     * Performs the full sync operation
     * @return true if successful, false if should retry
     */
    private suspend fun performSync(): Boolean {
        val device = scanForDevice() ?: run {
            Log.w(TAG, "BLE scan did not find bike tracker")
            return false
        }

        Log.d(TAG, "Found bike tracker: ${device.device.name}")

        // TODO: Connect to device and sync data
        // This will be implemented in A3 when we add the sync protocol
        // For now, we just verify scanning works

        return true
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

                    if (!resumed && result.device.name?.startsWith(DEVICE_NAME_PREFIX) == true) {
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
