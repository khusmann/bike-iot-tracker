package com.biketracker

import android.content.Context
import android.content.SharedPreferences

/**
 * Helper class for managing sync state persistence via SharedPreferences
 *
 * Stores local sync metadata to detect HealthConnect data loss and
 * provide diagnostic information for troubleshooting sync issues.
 */
class SyncPreferences(context: Context) {
    private val prefs: SharedPreferences = context.getSharedPreferences(
        PREFS_NAME,
        Context.MODE_PRIVATE
    )

    companion object {
        private const val PREFS_NAME = "bike_sync_prefs"

        // Keys
        private const val KEY_LAST_SYNC_SUCCESS_TIMESTAMP = "last_sync_success_timestamp"
        private const val KEY_LAST_SYNC_ATTEMPT_TIMESTAMP = "last_sync_attempt_timestamp"
        private const val KEY_LAST_SYNCED_SESSION_ID = "last_synced_session_id"
        private const val KEY_SYNC_SUCCESS_COUNT = "sync_success_count"
        private const val KEY_SYNC_FAILURE_COUNT = "sync_failure_count"
        private const val KEY_LAST_ERROR_MESSAGE = "last_error_message"
        private const val KEY_LAST_SYNCED_DEVICE_ADDRESS = "last_synced_device_address"
        private const val KEY_SYNC_INTERVAL_MINUTES = "sync_interval_minutes"
        private const val KEY_SYNC_ENABLED = "sync_enabled"
    }

    /**
     * Last successful sync timestamp (system time in milliseconds)
     */
    var lastSyncSuccessTimestamp: Long
        get() = prefs.getLong(KEY_LAST_SYNC_SUCCESS_TIMESTAMP, 0L)
        set(value) = prefs.edit().putLong(KEY_LAST_SYNC_SUCCESS_TIMESTAMP, value).apply()

    /**
     * Last sync attempt timestamp (system time in milliseconds)
     */
    var lastSyncAttemptTimestamp: Long
        get() = prefs.getLong(KEY_LAST_SYNC_ATTEMPT_TIMESTAMP, 0L)
        set(value) = prefs.edit().putLong(KEY_LAST_SYNC_ATTEMPT_TIMESTAMP, value).apply()

    /**
     * Last synced session ID (Unix timestamp from bike firmware)
     */
    var lastSyncedSessionId: Long
        get() = prefs.getLong(KEY_LAST_SYNCED_SESSION_ID, 0L)
        set(value) = prefs.edit().putLong(KEY_LAST_SYNCED_SESSION_ID, value).apply()

    /**
     * Total number of successful syncs
     */
    var syncSuccessCount: Int
        get() = prefs.getInt(KEY_SYNC_SUCCESS_COUNT, 0)
        set(value) = prefs.edit().putInt(KEY_SYNC_SUCCESS_COUNT, value).apply()

    /**
     * Total number of failed syncs
     */
    var syncFailureCount: Int
        get() = prefs.getInt(KEY_SYNC_FAILURE_COUNT, 0)
        set(value) = prefs.edit().putInt(KEY_SYNC_FAILURE_COUNT, value).apply()

    /**
     * Last error message (if any)
     */
    var lastErrorMessage: String?
        get() = prefs.getString(KEY_LAST_ERROR_MESSAGE, null)
        set(value) = prefs.edit().putString(KEY_LAST_ERROR_MESSAGE, value).apply()

    /**
     * Last synced device Bluetooth address
     */
    var lastSyncedDeviceAddress: String?
        get() = prefs.getString(KEY_LAST_SYNCED_DEVICE_ADDRESS, null)
        set(value) = prefs.edit().putString(KEY_LAST_SYNCED_DEVICE_ADDRESS, value).apply()

    /**
     * Sync interval in minutes (default: 60 minutes)
     */
    var syncIntervalMinutes: Int
        get() = prefs.getInt(KEY_SYNC_INTERVAL_MINUTES, 60)
        set(value) = prefs.edit().putInt(KEY_SYNC_INTERVAL_MINUTES, value).apply()

    /**
     * Whether periodic sync is enabled (default: false)
     */
    var syncEnabled: Boolean
        get() = prefs.getBoolean(KEY_SYNC_ENABLED, false)
        set(value) = prefs.edit().putBoolean(KEY_SYNC_ENABLED, value).apply()

    /**
     * Record a successful sync
     */
    fun recordSyncSuccess(deviceAddress: String, sessionId: Long) {
        val now = System.currentTimeMillis()
        prefs.edit().apply {
            putLong(KEY_LAST_SYNC_SUCCESS_TIMESTAMP, now)
            putLong(KEY_LAST_SYNC_ATTEMPT_TIMESTAMP, now)
            putLong(KEY_LAST_SYNCED_SESSION_ID, sessionId)
            putString(KEY_LAST_SYNCED_DEVICE_ADDRESS, deviceAddress)
            putInt(KEY_SYNC_SUCCESS_COUNT, syncSuccessCount + 1)
            putString(KEY_LAST_ERROR_MESSAGE, null)
            apply()
        }
    }

    /**
     * Record a failed sync
     */
    fun recordSyncFailure(errorMessage: String) {
        val now = System.currentTimeMillis()
        prefs.edit().apply {
            putLong(KEY_LAST_SYNC_ATTEMPT_TIMESTAMP, now)
            putInt(KEY_SYNC_FAILURE_COUNT, syncFailureCount + 1)
            putString(KEY_LAST_ERROR_MESSAGE, errorMessage)
            apply()
        }
    }

    /**
     * Clear all sync state (useful for testing)
     */
    fun clearAll() {
        prefs.edit().clear().apply()
    }
}
