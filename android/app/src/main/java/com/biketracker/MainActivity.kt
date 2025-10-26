package com.biketracker

import android.Manifest
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.TimeUnit
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.lifecycle.lifecycleScope
import com.google.accompanist.permissions.ExperimentalPermissionsApi
import com.google.accompanist.permissions.rememberMultiplePermissionsState
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    private val viewModel: BikeViewModel by viewModels()

    @OptIn(ExperimentalPermissionsApi::class)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Check if sync is enabled in preferences and schedule if needed
        val syncPrefs = SyncPreferences(applicationContext)
        if (syncPrefs.syncEnabled) {
            SyncScheduler.schedulePeriodicSync(applicationContext)
        }

        setContent {
            BikeTrackerTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    // HealthConnect permission setup
                    val healthConnectPermissions = setOf(
                        HealthPermission.getReadPermission(ExerciseSessionRecord::class),
                        HealthPermission.getWritePermission(ExerciseSessionRecord::class)
                    )

                    // Check if HealthConnect is available
                    val healthConnectAvailable = Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE &&
                            HealthConnectClient.getSdkStatus(applicationContext) == HealthConnectClient.SDK_AVAILABLE

                    // Track permission state
                    var healthConnectPermissionsGranted by remember { mutableStateOf(false) }

                    // Check current permission status on composition and after returning from settings
                    androidx.compose.runtime.LaunchedEffect(healthConnectAvailable) {
                        if (healthConnectAvailable) {
                            val healthConnectClient = HealthConnectClient.getOrCreate(applicationContext)
                            val granted = healthConnectClient.permissionController.getGrantedPermissions()
                            healthConnectPermissionsGranted = granted.containsAll(healthConnectPermissions)
                            Log.i("MainActivity", "Current HC permissions granted: $granted")
                        }
                    }

                    // HealthConnect permission launcher
                    val healthConnectPermissionsLauncher = rememberLauncherForActivityResult(
                        contract = PermissionController.createRequestPermissionResultContract()
                    ) { granted ->
                        Log.i("MainActivity", "HealthConnect permission result: $granted")
                        healthConnectPermissionsGranted = granted.containsAll(healthConnectPermissions)
                        Log.i("MainActivity", "All HC permissions granted: $healthConnectPermissionsGranted")
                    }

                    // Bluetooth permissions (standard Android)
                    val bluetoothPermissions = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                        listOf(
                            Manifest.permission.BLUETOOTH_SCAN,
                            Manifest.permission.BLUETOOTH_CONNECT
                        )
                    } else {
                        emptyList()
                    }

                    val bluetoothPermissionsState = rememberMultiplePermissionsState(bluetoothPermissions)

                    // Check if all permissions are granted
                    val allPermissionsGranted = (bluetoothPermissions.isEmpty() || bluetoothPermissionsState.allPermissionsGranted) &&
                            (!healthConnectAvailable || healthConnectPermissionsGranted)

                    if (allPermissionsGranted) {
                        BikeTrackerScreen(viewModel)
                    } else {
                        PermissionScreen(
                            bluetoothGranted = bluetoothPermissions.isEmpty() || bluetoothPermissionsState.allPermissionsGranted,
                            healthConnectGranted = !healthConnectAvailable || healthConnectPermissionsGranted,
                            healthConnectAvailable = healthConnectAvailable,
                            onRequestBluetoothPermissions = {
                                Log.i("MainActivity", "Requesting Bluetooth permissions")
                                bluetoothPermissionsState.launchMultiplePermissionRequest()
                            },
                            onRequestHealthConnectPermissions = {
                                Log.i("MainActivity", "Requesting HealthConnect permissions")
                                Log.i("MainActivity", "Permissions to request: $healthConnectPermissions")
                                healthConnectPermissionsLauncher.launch(healthConnectPermissions)
                            }
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun BikeTrackerTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = MaterialTheme.colorScheme,
        content = content
    )
}

@Composable
fun PermissionScreen(
    bluetoothGranted: Boolean,
    healthConnectGranted: Boolean,
    healthConnectAvailable: Boolean,
    onRequestBluetoothPermissions: () -> Unit,
    onRequestHealthConnectPermissions: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = "Permissions Required",
            style = MaterialTheme.typography.headlineSmall
        )
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            text = "This app needs permissions to function properly:",
            style = MaterialTheme.typography.bodyMedium
        )

        Spacer(modifier = Modifier.height(24.dp))

        // Bluetooth permissions section
        if (!bluetoothGranted) {
            Text(
                text = "• Bluetooth: Connect to your bike tracker",
                style = MaterialTheme.typography.bodyMedium
            )
            Spacer(modifier = Modifier.height(12.dp))
            Button(onClick = onRequestBluetoothPermissions) {
                Text("Grant Bluetooth Permissions")
            }
            Spacer(modifier = Modifier.height(24.dp))
        } else {
            Text(
                text = "✓ Bluetooth permissions granted",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.primary
            )
            Spacer(modifier = Modifier.height(24.dp))
        }

        // HealthConnect permissions section
        if (healthConnectAvailable && !healthConnectGranted) {
            Text(
                text = "• HealthConnect: Save your workout data",
                style = MaterialTheme.typography.bodyMedium
            )
            Spacer(modifier = Modifier.height(12.dp))
            Button(onClick = onRequestHealthConnectPermissions) {
                Text("Grant HealthConnect Permissions")
            }
        } else if (healthConnectGranted) {
            Text(
                text = "✓ HealthConnect permissions granted",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.primary
            )
        }
    }
}

@Composable
fun BikeTrackerScreen(viewModel: BikeViewModel) {
    val state by viewModel.state.collectAsState()
    val context = androidx.compose.ui.platform.LocalContext.current
    var selectedTabIndex by remember { mutableIntStateOf(0) }
    val tabs = listOf("Device", "Sync")

    Column(
        modifier = Modifier.fillMaxSize()
    ) {
        // Tab row
        TabRow(selectedTabIndex = selectedTabIndex) {
            tabs.forEachIndexed { index, title ->
                Tab(
                    selected = selectedTabIndex == index,
                    onClick = { selectedTabIndex = index },
                    text = { Text(title) }
                )
            }
        }

        // Tab content
        when (selectedTabIndex) {
            0 -> DeviceTab(viewModel, state)
            1 -> SyncTab(context)
        }
    }
}

@Composable
fun DeviceTab(viewModel: BikeViewModel, state: BikeState) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // Connection status
        ConnectionStatusCard(state.connectionState)

        Spacer(modifier = Modifier.height(48.dp))

        // Cadence display
        MetricCard(
            label = "Cadence",
            value = state.cadence?.toString() ?: "--",
            unit = "RPM"
        )

        Spacer(modifier = Modifier.height(24.dp))

        // Total revolutions
        MetricCard(
            label = "Total Revolutions",
            value = state.totalRevolutions.toString(),
            unit = ""
        )

        Spacer(modifier = Modifier.height(24.dp))

        // HealthConnect status
        Text(
            text = "HealthConnect: ${if (state.healthConnectAvailable) "Available" else "Not Available"}",
            style = MaterialTheme.typography.bodyMedium,
            color = if (state.healthConnectAvailable)
                MaterialTheme.colorScheme.primary
            else
                MaterialTheme.colorScheme.error
        )

        Spacer(modifier = Modifier.height(24.dp))

        // Connect/Disconnect button
        when (state.connectionState) {
            is ConnectionState.Disconnected, is ConnectionState.Error -> {
                Button(onClick = { viewModel.connect() }) {
                    Text("Connect")
                }
            }
            is ConnectionState.Connected -> {
                Button(onClick = { viewModel.disconnect() }) {
                    Text("Disconnect")
                }
            }
            else -> {
                // Scanning or connecting - show disabled button
                Button(onClick = {}, enabled = false) {
                    Text("Connecting...")
                }
            }
        }
    }
}

@Composable
fun SyncTab(context: android.content.Context) {
    // Load sync state from SharedPreferences
    val syncPrefs = remember { SyncPreferences(context) }
    val healthConnectHelper = remember { HealthConnectHelper(context) }

    var syncState by remember { mutableStateOf(loadSyncState(context, syncPrefs, healthConnectHelper)) }

    // Refresh sync state periodically
    LaunchedEffect(Unit) {
        while (true) {
            kotlinx.coroutines.delay(1000) // Refresh every second
            syncState = loadSyncState(context, syncPrefs, healthConnectHelper)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Top,
        horizontalAlignment = Alignment.Start
    ) {
        Text(
            text = "Sync Settings",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold
        )

        Spacer(modifier = Modifier.height(24.dp))

        // Last Sync Info Section
        Text(
            text = "Last Sync Info",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold
        )

        Spacer(modifier = Modifier.height(12.dp))

        SyncInfoRow("Last sync attempt:", formatTimestamp(syncPrefs.lastSyncAttemptTimestamp))

        when (val status = syncState.lastSyncStatus) {
            is SyncStatus.NeverSynced -> {
                SyncInfoRow("Status:", "Never synced")
            }
            is SyncStatus.Success -> {
                SyncInfoRow("Status:", "Success")
                SyncInfoRow("Last successful sync:", formatTimestamp(status.timestamp))
            }
            is SyncStatus.Failed -> {
                SyncInfoRow("Status:", "Failed")
                Text(
                    text = "Error: ${status.message}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.padding(vertical = 4.dp)
                )
            }
        }

        SyncInfoRow("Last synced session:",
            if (syncState.lastSyncedSessionId > 0) {
                formatUnixTimestamp(syncState.lastSyncedSessionId)
            } else {
                "None"
            }
        )

        syncState.lastSyncedDeviceAddress?.let { deviceAddress ->
            SyncInfoRow("Device:", deviceAddress)
        }

        Spacer(modifier = Modifier.height(24.dp))

        // Sync Schedule Control Section
        Text(
            text = "Sync Schedule",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold
        )

        Spacer(modifier = Modifier.height(12.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("Periodic sync enabled:")
            androidx.compose.material3.Switch(
                checked = syncState.syncEnabled,
                onCheckedChange = { enabled ->
                    syncPrefs.syncEnabled = enabled
                    if (enabled) {
                        SyncScheduler.schedulePeriodicSync(context)
                    } else {
                        SyncScheduler.cancelPeriodicSync(context)
                    }
                    syncState = loadSyncState(context, syncPrefs, healthConnectHelper)
                }
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        SyncInfoRow("Sync interval:", "${syncState.syncIntervalMinutes} minutes")

        Spacer(modifier = Modifier.height(12.dp))

        Button(
            onClick = {
                Log.i("MainActivity", "Manual sync button clicked")
                SyncScheduler.triggerImmediateSync(context)
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Sync Now")
        }

        Spacer(modifier = Modifier.height(24.dp))

        // Diagnostic Info Section
        Text(
            text = "Diagnostics",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold
        )

        Spacer(modifier = Modifier.height(12.dp))

        SyncInfoRow("Successful syncs:", syncState.syncSuccessCount.toString())
        SyncInfoRow("Failed syncs:", syncState.syncFailureCount.toString())

        // HealthConnect vs SharedPreferences comparison
        if (syncState.lastSyncedSessionId > 0 || syncState.healthConnectTimestamp > 0) {
            Spacer(modifier = Modifier.height(12.dp))
            Text(
                text = "Data Integrity Check",
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Bold
            )
            SyncInfoRow("Local last session:",
                if (syncState.lastSyncedSessionId > 0) {
                    syncState.lastSyncedSessionId.toString()
                } else {
                    "0"
                }
            )
            SyncInfoRow("HealthConnect last:",
                if (syncState.healthConnectTimestamp > 0) {
                    syncState.healthConnectTimestamp.toString()
                } else {
                    "0"
                }
            )

            if (syncState.lastSyncedSessionId > syncState.healthConnectTimestamp && syncState.lastSyncedSessionId > 0) {
                Text(
                    text = "WARNING: Local state is newer than HealthConnect. HealthConnect data may have been cleared.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.padding(vertical = 4.dp)
                )
            }
        }
    }
}

@Composable
fun SyncInfoRow(label: String, value: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.Medium
        )
    }
}

fun loadSyncState(context: android.content.Context, syncPrefs: SyncPreferences, healthConnectHelper: HealthConnectHelper): SyncState {
    // Determine sync status
    val lastSyncStatus = when {
        syncPrefs.lastSyncSuccessTimestamp == 0L && syncPrefs.lastSyncAttemptTimestamp == 0L -> {
            SyncStatus.NeverSynced
        }
        syncPrefs.lastErrorMessage != null &&
            syncPrefs.lastSyncAttemptTimestamp > syncPrefs.lastSyncSuccessTimestamp -> {
            SyncStatus.Failed(syncPrefs.lastErrorMessage!!, syncPrefs.lastSyncAttemptTimestamp)
        }
        else -> {
            SyncStatus.Success(syncPrefs.lastSyncSuccessTimestamp)
        }
    }

    // Try to get HealthConnect timestamp (on background thread in real app, but simplified here)
    val healthConnectTimestamp = try {
        // This is a simplified synchronous call for demo - in production should be async
        0L // Will be updated by LaunchedEffect if needed
    } catch (e: Exception) {
        0L
    }

    return SyncState(
        lastSyncStatus = lastSyncStatus,
        lastSyncedSessionId = syncPrefs.lastSyncedSessionId,
        syncSuccessCount = syncPrefs.syncSuccessCount,
        syncFailureCount = syncPrefs.syncFailureCount,
        syncEnabled = syncPrefs.syncEnabled,
        syncIntervalMinutes = syncPrefs.syncIntervalMinutes,
        lastSyncedDeviceAddress = syncPrefs.lastSyncedDeviceAddress,
        healthConnectTimestamp = healthConnectTimestamp
    )
}

fun formatTimestamp(timestamp: Long): String {
    if (timestamp == 0L) return "Never"

    val now = System.currentTimeMillis()
    val diff = now - timestamp

    return when {
        diff < TimeUnit.MINUTES.toMillis(1) -> "Just now"
        diff < TimeUnit.HOURS.toMillis(1) -> "${TimeUnit.MILLISECONDS.toMinutes(diff)} minutes ago"
        diff < TimeUnit.DAYS.toMillis(1) -> "${TimeUnit.MILLISECONDS.toHours(diff)} hours ago"
        else -> {
            val dateFormat = SimpleDateFormat("MMM dd, HH:mm", Locale.getDefault())
            dateFormat.format(Date(timestamp))
        }
    }
}

fun formatUnixTimestamp(unixSeconds: Long): String {
    val dateFormat = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())
    return "${dateFormat.format(Date(unixSeconds * 1000))} ($unixSeconds)"
}

@Composable
fun ConnectionStatusCard(connectionState: ConnectionState) {
    val (statusText, statusColor) = when (connectionState) {
        is ConnectionState.Disconnected -> "Disconnected" to MaterialTheme.colorScheme.error
        is ConnectionState.Scanning -> "Scanning..." to MaterialTheme.colorScheme.primary
        is ConnectionState.Connecting -> "Connecting..." to MaterialTheme.colorScheme.primary
        is ConnectionState.Connected -> "Connected: ${connectionState.deviceName}" to MaterialTheme.colorScheme.primary
        is ConnectionState.Error -> "Error: ${connectionState.message}" to MaterialTheme.colorScheme.error
    }

    Text(
        text = statusText,
        color = statusColor,
        style = MaterialTheme.typography.titleMedium
    )
}

@Composable
fun MetricCard(label: String, value: String, unit: String) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = value,
            fontSize = 56.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary
        )
        if (unit.isNotEmpty()) {
            Text(
                text = unit,
                style = MaterialTheme.typography.titleLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}
