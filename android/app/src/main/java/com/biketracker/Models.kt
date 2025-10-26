package com.biketracker

/**
 * Immutable data models for the bike tracker app
 */

/**
 * Represents a CSC (Cycling Speed and Cadence) measurement
 *
 * @property cumulativeRevolutions Total crank revolutions (UINT16, wraps at 65536)
 * @property lastEventTime Time of last crank event in 1/1024 second units (UINT16)
 */
data class CscMeasurement(
    val cumulativeRevolutions: UShort,
    val lastEventTime: UShort
)

/**
 * BLE connection state
 */
sealed class ConnectionState {
    data object Disconnected : ConnectionState()
    data object Scanning : ConnectionState()
    data object Connecting : ConnectionState()
    data class Connected(val deviceName: String) : ConnectionState()
    data class Error(val message: String) : ConnectionState()
}

/**
 * BLE events emitted during connection lifecycle
 */
sealed class BleEvent {
    data class ConnectionEstablished(val deviceName: String) : BleEvent()
    data class MeasurementReceived(val measurement: CscMeasurement) : BleEvent()
    data class ConnectionError(val message: String) : BleEvent()
}

/**
 * Bike telemetry state
 *
 * @property cadence Current cadence in RPM (null if no recent data)
 * @property totalRevolutions Total crank revolutions (UINT16, wraps at 65536)
 * @property connectionState Current BLE connection state
 * @property healthConnectAvailable Whether HealthConnect is available on this device
 */
data class BikeState(
    val cadence: Int? = null,
    val totalRevolutions: UShort = 0u,
    val connectionState: ConnectionState = ConnectionState.Disconnected,
    val healthConnectAvailable: Boolean = false
)

/**
 * Sync status for display in UI
 */
sealed class SyncStatus {
    data object NeverSynced : SyncStatus()
    data class Success(val timestamp: Long) : SyncStatus()
    data class Failed(val message: String, val timestamp: Long) : SyncStatus()
}

/**
 * Sync state for the sync settings tab
 *
 * Note: syncEnabled is NOT stored here - it's managed via SharedPreferences
 * Note: syncInterval is NOT stored here - it's a constant in SyncScheduler
 *
 * @property lastSyncStatus Status of the last sync attempt
 * @property lastSyncedSessionId Unix timestamp of the last synced session
 * @property syncSuccessCount Total number of successful syncs
 * @property syncFailureCount Total number of failed syncs
 * @property lastSyncedDeviceAddress Bluetooth address of last synced device
 * @property healthConnectTimestamp Last sync timestamp from HealthConnect (for comparison)
 * @property targetDeviceAddress Target device address for sync (null = any device)
 * @property targetDeviceName Target device name for display
 */
data class SyncState(
    val lastSyncStatus: SyncStatus = SyncStatus.NeverSynced,
    val lastSyncedSessionId: Long = 0L,
    val syncSuccessCount: Int = 0,
    val syncFailureCount: Int = 0,
    val lastSyncedDeviceAddress: String? = null,
    val healthConnectTimestamp: Long = 0L,
    val targetDeviceAddress: String? = null,
    val targetDeviceName: String? = null
)

/**
 * Calculates cadence (RPM) from two consecutive CSC measurements
 *
 * With 1 Hz continuous notifications, the firmware sends updates even when idle.
 * When no new revolutions occur, both revDiff and timeDiff will be 0, indicating
 * the user has stopped pedaling (cadence = 0 RPM).
 *
 * @param prev Previous CSC measurement
 * @param curr Current CSC measurement
 * @return Cadence in RPM, or null if this is the first measurement
 */
fun calculateCadence(prev: CscMeasurement?, curr: CscMeasurement): Int? {
    if (prev == null) return null

    val revDiff = (curr.cumulativeRevolutions - prev.cumulativeRevolutions).toInt()

    // If no new revolutions, user has stopped pedaling
    if (revDiff == 0) return 0

    // Negative revDiff shouldn't happen, but if it does, ignore this measurement
    if (revDiff < 0) return null

    // Handle time wraparound (UShort wraps at 65536)
    val timeDiff = if (curr.lastEventTime >= prev.lastEventTime) {
        (curr.lastEventTime - prev.lastEventTime).toInt()
    } else {
        (65536 + curr.lastEventTime.toInt() - prev.lastEventTime.toInt())
    }

    if (timeDiff <= 0) return null

    // Convert to RPM: (revolutions * 1024 * 60) / time_in_1024th_seconds
    val cadence = (revDiff * 1024 * 60) / timeDiff

    // Sanity check: cadence should be between 0 and 300 RPM
    return if (cadence in 0..300) cadence else null
}
