package com.biketracker

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
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

    private val bleManager = BleManager(application)

    private val _state = MutableStateFlow(BikeState())
    val state: StateFlow<BikeState> = _state.asStateFlow()

    private var previousMeasurement: CscMeasurement? = null

    /**
     * Starts BLE connection and begins receiving measurements
     */
    fun connect() {
        viewModelScope.launch {
            _state.value = _state.value.copy(connectionState = ConnectionState.Scanning)

            bleManager.connect().collect { result ->
                result.fold(
                    onSuccess = { measurement ->
                        updateState(measurement)
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
     * Updates state with new CSC measurement
     */
    private fun updateState(measurement: CscMeasurement) {
        val cadence = calculateCadence(previousMeasurement, measurement)

        _state.value = BikeState(
            cadence = cadence,
            totalRevolutions = measurement.cumulativeRevolutions,
            connectionState = ConnectionState.Connected("BikeTracker")
        )

        previousMeasurement = measurement
    }

    /**
     * Disconnects from device
     */
    fun disconnect() {
        bleManager.disconnect()
        _state.value = BikeState()
        previousMeasurement = null
    }

    override fun onCleared() {
        super.onCleared()
        bleManager.disconnect()
    }
}
