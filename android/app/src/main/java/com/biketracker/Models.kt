package com.biketracker

/**
 * Immutable data models for the bike tracker app
 */

/**
 * Represents a CSC (Cycling Speed and Cadence) measurement
 *
 * @property cumulativeRevolutions Total crank revolutions since tracking started
 * @property lastEventTime Time of last crank event in 1/1024 second units
 */
data class CscMeasurement(
    val cumulativeRevolutions: UInt,
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
 * @property totalRevolutions Total crank revolutions
 * @property connectionState Current BLE connection state
 */
data class BikeState(
    val cadence: Int? = null,
    val totalRevolutions: UInt = 0u,
    val connectionState: ConnectionState = ConnectionState.Disconnected
)

/**
 * Calculates cadence (RPM) from two consecutive CSC measurements
 *
 * @param prev Previous CSC measurement
 * @param curr Current CSC measurement
 * @return Cadence in RPM, or null if calculation is not possible
 */
fun calculateCadence(prev: CscMeasurement?, curr: CscMeasurement): Int? {
    if (prev == null) return null

    val revDiff = (curr.cumulativeRevolutions - prev.cumulativeRevolutions).toInt()
    if (revDiff <= 0) return null

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
