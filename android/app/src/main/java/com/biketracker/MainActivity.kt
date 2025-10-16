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
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
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

        // Schedule background sync (KEEP policy means won't reschedule if already scheduled)
        SyncScheduler.schedulePeriodicSync(applicationContext)

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

        // Test button for querying last synced timestamp
        if (state.healthConnectAvailable) {
            Button(onClick = {
                // Test with a dummy bike address
                Log.i("MainActivity", "Test button clicked - querying last synced timestamp")
                viewModel.testQueryLastSyncedTimestamp("AA:BB:CC:DD:EE:FF")
            }) {
                Text("Test HealthConnect Query")
            }
        }

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
