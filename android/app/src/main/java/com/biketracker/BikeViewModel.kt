package com.biketracker

import android.app.Application
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * ViewModel for managing bike tracker state
 *
 * Follows functional patterns with immutable state updates
 */
class BikeViewModel(application: Application) : AndroidViewModel(application) {

    companion object {
        private const val TAG = "BikeViewModel"
    }

    private val bleManager = BleManager(application)
    private val healthConnectHelper = HealthConnectHelper(application)

    private val _state = MutableStateFlow(BikeState())
    val state: StateFlow<BikeState> = _state.asStateFlow()

    private var previousMeasurement: CscMeasurement? = null
    private var cadenceTimeoutJob: Job? = null

    init {
        // Check HealthConnect availability on initialization
        val isHealthConnectAvailable = healthConnectHelper.isAvailable()
        _state.value = _state.value.copy(healthConnectAvailable = isHealthConnectAvailable)
        Log.i(TAG, "HealthConnect available: $isHealthConnectAvailable")
    }

    /**
     * Starts BLE connection and begins receiving measurements
     */
    fun connect() {
        viewModelScope.launch {
            _state.value = _state.value.copy(connectionState = ConnectionState.Scanning)

            bleManager.connect().collect { result ->
                result.fold(
                    onSuccess = { event ->
                        handleBleEvent(event)
                    },
                    onFailure = { error ->
                        _state.value = _state.value.copy(
                            connectionState = ConnectionState.Error(
                                error.message ?: "Unknown error"
                            )
                        )
                    }
                )
            }
        }
    }

    /**
     * Handles BLE events (connection, measurements, errors)
     */
    private fun handleBleEvent(event: BleEvent) {
        when (event) {
            is BleEvent.ConnectionEstablished -> {
                _state.value = _state.value.copy(
                    connectionState = ConnectionState.Connected(event.deviceName)
                )
            }
            is BleEvent.MeasurementReceived -> {
                updateMeasurement(event.measurement)
            }
            is BleEvent.ConnectionError -> {
                _state.value = _state.value.copy(
                    connectionState = ConnectionState.Error(event.message)
                )
            }
        }
    }

    /**
     * Updates state with new CSC measurement
     *
     * With 1 Hz continuous notifications, we receive updates even when idle.
     * The calculateCadence function returns 0 when there are no new revolutions,
     * allowing real-time display of 0 RPM without needing a timeout.
     */
    private fun updateMeasurement(measurement: CscMeasurement) {
        val newCadence = calculateCadence(previousMeasurement, measurement)
        Log.d(TAG, "Updating measurement: revolutions=${measurement.cumulativeRevolutions}, cadence=$newCadence")

        // Update state with new cadence (can be 0 for idle, or null for first measurement)
        _state.value = _state.value.copy(
            cadence = newCadence,
            totalRevolutions = measurement.cumulativeRevolutions
        )

        // Cancel any existing timeout since we're receiving continuous updates
        cadenceTimeoutJob?.cancel()
        cadenceTimeoutJob = null

        previousMeasurement = measurement
    }

    /**
     * Disconnects from device
     */
    fun disconnect() {
        bleManager.disconnect()
        cadenceTimeoutJob?.cancel()
        cadenceTimeoutJob = null
        // Reset state but preserve HealthConnect availability
        _state.value = BikeState(
            healthConnectAvailable = _state.value.healthConnectAvailable
        )
        previousMeasurement = null
    }

    /**
     * Test function: Query last synced timestamp for a given bike address
     * This is useful for testing the HealthConnect integration
     */
    fun testQueryLastSyncedTimestamp(bikeAddress: String) {
        viewModelScope.launch {
            val timestamp = healthConnectHelper.getLastSyncedTimestamp(bikeAddress)
            Log.i(TAG, "Last synced timestamp for bike $bikeAddress: $timestamp")
            // Could update state here to show in UI if desired
        }
    }

    override fun onCleared() {
        super.onCleared()
        bleManager.disconnect()
        cadenceTimeoutJob?.cancel()
    }
}
