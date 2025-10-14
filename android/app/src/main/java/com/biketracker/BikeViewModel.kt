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
        private const val CADENCE_TIMEOUT_MS = 3000L // Reset cadence after 3 seconds of no new revolutions
    }

    private val bleManager = BleManager(application)

    private val _state = MutableStateFlow(BikeState())
    val state: StateFlow<BikeState> = _state.asStateFlow()

    private var previousMeasurement: CscMeasurement? = null
    private var cadenceTimeoutJob: Job? = null

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
     */
    private fun updateMeasurement(measurement: CscMeasurement) {
        val newCadence = calculateCadence(previousMeasurement, measurement)
        Log.d(TAG, "Updating measurement: revolutions=${measurement.cumulativeRevolutions}, cadence=$newCadence")

        // If we have a new valid cadence, update it and reset the timeout
        if (newCadence != null) {
            _state.value = _state.value.copy(
                cadence = newCadence,
                totalRevolutions = measurement.cumulativeRevolutions
            )

            // Cancel any existing timeout and start a new one
            cadenceTimeoutJob?.cancel()
            cadenceTimeoutJob = viewModelScope.launch {
                delay(CADENCE_TIMEOUT_MS)
                // Reset cadence to null after timeout
                _state.value = _state.value.copy(cadence = null)
                Log.d(TAG, "Cadence timeout - resetting to null")
            }
        } else {
            // No new revolutions, just update total revolutions
            _state.value = _state.value.copy(
                totalRevolutions = measurement.cumulativeRevolutions
            )
        }

        previousMeasurement = measurement
    }

    /**
     * Disconnects from device
     */
    fun disconnect() {
        bleManager.disconnect()
        cadenceTimeoutJob?.cancel()
        cadenceTimeoutJob = null
        _state.value = BikeState()
        previousMeasurement = null
    }

    override fun onCleared() {
        super.onCleared()
        bleManager.disconnect()
        cadenceTimeoutJob?.cancel()
    }
}
