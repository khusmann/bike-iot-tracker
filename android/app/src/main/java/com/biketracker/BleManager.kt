package com.biketracker

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattDescriptor
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.os.ParcelUuid
import android.util.Log
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.UUID

/**
 * BLE Manager for connecting to bike tracker and receiving CSC measurements
 *
 * Uses functional patterns with Kotlin Flow for reactive updates
 */
class BleManager(private val context: Context) {

    companion object {
        private const val TAG = "BleManager"

        // Cycling Speed and Cadence Service
        private val CSC_SERVICE_UUID = UUID.fromString("00001816-0000-1000-8000-00805f9b34fb")
        private val CSC_MEASUREMENT_UUID = UUID.fromString("00002a5b-0000-1000-8000-00805f9b34fb")
        private val CLIENT_CHARACTERISTIC_CONFIG_UUID = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")

        private const val DEVICE_NAME_PREFIX = "BikeTracker"
    }

    private val bluetoothAdapter: BluetoothAdapter? by lazy {
        val bluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
        bluetoothManager.adapter
    }

    private var bluetoothGatt: BluetoothGatt? = null

    /**
     * Scans for and connects to the bike tracker device, emitting BLE events
     *
     * @return Flow of BLE events (connection established, measurements, errors)
     */
    @SuppressLint("MissingPermission")
    fun connect(): Flow<Result<BleEvent>> = callbackFlow {
        val adapter = bluetoothAdapter
        if (adapter == null || !adapter.isEnabled) {
            trySend(Result.failure(Exception("Bluetooth not available or disabled")))
            close()
            return@callbackFlow
        }

        val scanner = adapter.bluetoothLeScanner
        if (scanner == null) {
            trySend(Result.failure(Exception("BLE scanner not available")))
            close()
            return@callbackFlow
        }

        val scanCallback = object : ScanCallback() {
            override fun onScanResult(callbackType: Int, result: ScanResult) {
                Log.d(TAG, "Found device: ${result.device.name}")
                scanner.stopScan(this)

                // Connect to device
                val gattCallback = object : BluetoothGattCallback() {
                    override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
                        when (newState) {
                            BluetoothProfile.STATE_CONNECTED -> {
                                Log.d(TAG, "Connected to GATT server")
                                trySend(Result.success(BleEvent.ConnectionEstablished(result.device.name ?: "BikeTracker")))
                                gatt.discoverServices()
                            }
                            BluetoothProfile.STATE_DISCONNECTED -> {
                                Log.d(TAG, "Disconnected from GATT server")
                                trySend(Result.success(BleEvent.ConnectionError("Disconnected")))
                                close()
                            }
                        }
                    }

                    override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
                        if (status == BluetoothGatt.GATT_SUCCESS) {
                            val service = gatt.getService(CSC_SERVICE_UUID)
                            val characteristic = service?.getCharacteristic(CSC_MEASUREMENT_UUID)

                            if (characteristic != null) {
                                // Enable notifications
                                gatt.setCharacteristicNotification(characteristic, true)

                                // Write to descriptor to enable notifications
                                val descriptor = characteristic.getDescriptor(CLIENT_CHARACTERISTIC_CONFIG_UUID)
                                descriptor?.let {
                                    it.value = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
                                    gatt.writeDescriptor(it)
                                }
                                Log.d(TAG, "Requesting CSC notifications")
                            } else {
                                trySend(Result.success(BleEvent.ConnectionError("CSC characteristic not found")))
                                close()
                            }
                        }
                    }

                    override fun onDescriptorWrite(
                        gatt: BluetoothGatt,
                        descriptor: BluetoothGattDescriptor,
                        status: Int
                    ) {
                        if (status == BluetoothGatt.GATT_SUCCESS) {
                            if (descriptor.uuid == CLIENT_CHARACTERISTIC_CONFIG_UUID) {
                                Log.d(TAG, "CSC notifications enabled successfully")
                            }
                        } else {
                            Log.e(TAG, "Failed to enable notifications: $status")
                            trySend(Result.success(BleEvent.ConnectionError("Failed to enable notifications")))
                        }
                    }

                    override fun onCharacteristicChanged(
                        gatt: BluetoothGatt,
                        characteristic: BluetoothGattCharacteristic,
                        value: ByteArray
                    ) {
                        if (characteristic.uuid == CSC_MEASUREMENT_UUID) {
                            Log.d(TAG, "CSC measurement received: ${value.size} bytes")
                            parseCscMeasurement(value)?.let { measurement ->
                                Log.d(TAG, "Parsed: revolutions=${measurement.cumulativeRevolutions}, time=${measurement.lastEventTime}")
                                trySend(Result.success(BleEvent.MeasurementReceived(measurement)))
                            }
                        }
                    }
                }

                bluetoothGatt = result.device.connectGatt(context, false, gattCallback)
            }

            override fun onScanFailed(errorCode: Int) {
                Log.e(TAG, "Scan failed with error: $errorCode")
                trySend(Result.success(BleEvent.ConnectionError("Scan failed: $errorCode")))
                close()
            }
        }

        // Start scanning with filters
        val scanFilter = ScanFilter.Builder()
            .setServiceUuid(ParcelUuid(CSC_SERVICE_UUID))
            .build()

        val scanSettings = ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
            .build()

        Log.d(TAG, "Starting BLE scan")
        scanner.startScan(listOf(scanFilter), scanSettings, scanCallback)

        awaitClose {
            scanner.stopScan(scanCallback)
            bluetoothGatt?.close()
            bluetoothGatt = null
        }
    }

    /**
     * Parses CSC Measurement characteristic data
     *
     * Format (per BLE CSC spec):
     * - Byte 0: Flags (0x02 = crank data present)
     * - Bytes 1-2: Cumulative Crank Revolutions (uint16)
     * - Bytes 3-4: Last Crank Event Time (uint16, 1/1024 second units)
     *
     * @param data Raw characteristic data
     * @return Parsed CSC measurement, or null if parsing fails
     */
    private fun parseCscMeasurement(data: ByteArray): CscMeasurement? {
        if (data.size < 5) {
            Log.w(TAG, "CSC data too short: ${data.size} bytes")
            return null
        }

        return try {
            val buffer = ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN)
            buffer.get() // Skip flags

            val cumulativeRevolutions = buffer.short.toUShort()
            val lastEventTime = buffer.short.toUShort()

            CscMeasurement(cumulativeRevolutions, lastEventTime)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse CSC measurement", e)
            null
        }
    }

    /**
     * Disconnects from the current device
     */
    @SuppressLint("MissingPermission")
    fun disconnect() {
        bluetoothGatt?.disconnect()
        bluetoothGatt?.close()
        bluetoothGatt = null
    }
}
