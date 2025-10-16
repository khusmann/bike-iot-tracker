package com.biketracker

import android.content.Context
import android.os.Build
import android.util.Log
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import java.time.Instant

/**
 * Helper class for interacting with HealthConnect.
 *
 * Provides functionality to:
 * - Check HealthConnect availability
 * - Query the last synced session for a specific bike
 * - Write exercise sessions to HealthConnect
 */
class HealthConnectHelper(private val context: Context) {

    private val tag = "HealthConnectHelper"

    /**
     * Check if HealthConnect is available on this device.
     *
     * Requirements:
     * - Android API 28+ (Android 9.0)
     * - HealthConnect SDK available
     *
     * @return true if HealthConnect is available, false otherwise
     */
    fun isAvailable(): Boolean {
        // HealthConnect requires API 28+
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.P) {
            Log.w(tag, "HealthConnect not available: requires API 28+")
            return false
        }

        // Check if HealthConnect SDK is available
        val availability = HealthConnectClient.getSdkStatus(context)
        return when (availability) {
            HealthConnectClient.SDK_AVAILABLE -> {
                Log.i(tag, "HealthConnect is available")
                true
            }
            HealthConnectClient.SDK_UNAVAILABLE -> {
                Log.w(tag, "HealthConnect SDK is unavailable")
                false
            }
            HealthConnectClient.SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED -> {
                Log.w(tag, "HealthConnect requires provider update")
                false
            }
            else -> {
                Log.w(tag, "Unknown HealthConnect availability status: $availability")
                false
            }
        }
    }

    /**
     * Get a HealthConnect client instance.
     *
     * @return HealthConnectClient if available, null otherwise
     */
    private fun getClient(): HealthConnectClient? {
        return if (isAvailable()) {
            HealthConnectClient.getOrCreate(context)
        } else {
            null
        }
    }

    /**
     * Query HealthConnect for the last synced session for a specific bike.
     *
     * Sessions are identified by their clientRecordId in the format:
     * "bike-{bikeAddress}-{startTime}"
     *
     * This method queries all exercise sessions (descending order) and filters
     * for sessions from this bike, returning the maximum start time found.
     *
     * @param bikeAddress Bluetooth device address (e.g., "AA:BB:CC:DD:EE:FF")
     * @return Unix timestamp (seconds) of the last synced session, or 0 if none found
     */
    suspend fun getLastSyncedTimestamp(bikeAddress: String): Long {
        val client = getClient() ?: return 0L

        try {
            // Query all exercise sessions in descending order (most recent first)
            // Use a time range from epoch to far future to get all records
            val request = ReadRecordsRequest(
                recordType = ExerciseSessionRecord::class,
                timeRangeFilter = TimeRangeFilter.between(
                    Instant.ofEpochSecond(0),
                    Instant.ofEpochSecond(4102444800) // Jan 1, 2100
                ),
                ascendingOrder = false
            )

            val response = client.readRecords(request)
            val prefix = "bike-$bikeAddress-"

            // Find the most recent session for this bike
            val lastSession = response.records.firstOrNull { record ->
                record.metadata.clientRecordId?.startsWith(prefix) == true
            }

            return if (lastSession != null) {
                val timestamp = lastSession.startTime.epochSecond
                Log.i(tag, "Last synced session for bike $bikeAddress: $timestamp")
                timestamp
            } else {
                Log.i(tag, "No previous sessions found for bike $bikeAddress")
                0L
            }
        } catch (e: Exception) {
            Log.e(tag, "Error querying last synced timestamp for bike $bikeAddress", e)
            return 0L
        }
    }

    /**
     * Get the required HealthConnect permissions for this app.
     */
    companion object {
        val REQUIRED_PERMISSIONS = setOf(
            HealthPermission.getReadPermission(ExerciseSessionRecord::class),
            HealthPermission.getWritePermission(ExerciseSessionRecord::class)
        )
    }
}
