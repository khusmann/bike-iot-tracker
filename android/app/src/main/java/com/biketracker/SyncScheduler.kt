package com.biketracker

import android.content.Context
import android.util.Log
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

/**
 * Manages scheduling of background sync worker
 *
 * Sets up periodic WorkManager job to sync bike tracker data in the background
 */
object SyncScheduler {

    private const val TAG = "BikeSync"

    /**
     * Schedule periodic background sync
     *
     * For testing: uses 15-minute interval (minimum allowed by WorkManager)
     * For production: should be changed to hourly or longer
     *
     * @param context Application context
     */
    fun schedulePeriodicSync(context: Context) {
        val constraints = Constraints.Builder()
            // Don't require network for BLE sync
            .setRequiredNetworkType(NetworkType.NOT_REQUIRED)
            .build()

        val syncWorkRequest = PeriodicWorkRequestBuilder<BackgroundSyncWorker>(
            // Use 15 minutes for testing (minimum allowed)
            // Change to 1 hour for production: 1, TimeUnit.HOURS
            15, TimeUnit.MINUTES
        )
            .setConstraints(constraints)
            .build()

        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            BackgroundSyncWorker.WORK_NAME,
            // KEEP means if work is already scheduled, don't replace it
            ExistingPeriodicWorkPolicy.KEEP,
            syncWorkRequest
        )

        Log.d(TAG, "Background sync scheduling ensured (every 15 minutes, KEEP policy)")
    }

    /**
     * Trigger an immediate one-time sync
     *
     * This bypasses the periodic schedule and runs a sync immediately.
     * Useful for manual sync triggers from the UI.
     *
     * @param context Application context
     */
    fun triggerImmediateSync(context: Context) {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.NOT_REQUIRED)
            .build()

        val syncWorkRequest = OneTimeWorkRequestBuilder<BackgroundSyncWorker>()
            .setConstraints(constraints)
            .build()

        WorkManager.getInstance(context).enqueueUniqueWork(
            "${BackgroundSyncWorker.WORK_NAME}_manual",
            // KEEP means if a manual sync is already running, don't start another
            ExistingWorkPolicy.KEEP,
            syncWorkRequest
        )

        Log.d(TAG, "Manual sync triggered")
    }

    /**
     * Cancel all background sync work
     *
     * @param context Application context
     */
    fun cancelSync(context: Context) {
        WorkManager.getInstance(context).cancelUniqueWork(BackgroundSyncWorker.WORK_NAME)
        Log.d(TAG, "Periodic background sync cancelled")
    }

    /**
     * Cancel periodic background sync (alias for cancelSync)
     *
     * @param context Application context
     */
    fun cancelPeriodicSync(context: Context) {
        cancelSync(context)
    }
}
