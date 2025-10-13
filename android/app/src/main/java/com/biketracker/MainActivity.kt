package com.biketracker

import android.Manifest
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.google.accompanist.permissions.ExperimentalPermissionsApi
import com.google.accompanist.permissions.rememberMultiplePermissionsState

class MainActivity : ComponentActivity() {

    private val viewModel: BikeViewModel by viewModels()

    @OptIn(ExperimentalPermissionsApi::class)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            BikeTrackerTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val permissions = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                        listOf(
                            Manifest.permission.BLUETOOTH_SCAN,
                            Manifest.permission.BLUETOOTH_CONNECT
                        )
                    } else {
                        emptyList()
                    }

                    val permissionsState = rememberMultiplePermissionsState(permissions)

                    if (permissions.isEmpty() || permissionsState.allPermissionsGranted) {
                        BikeTrackerScreen(viewModel)
                    } else {
                        PermissionScreen(
                            onRequestPermissions = { permissionsState.launchMultiplePermissionRequest() }
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
fun PermissionScreen(onRequestPermissions: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = "Bluetooth permissions required",
            style = MaterialTheme.typography.headlineSmall
        )
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            text = "This app needs Bluetooth permissions to connect to your bike tracker.",
            style = MaterialTheme.typography.bodyMedium
        )
        Spacer(modifier = Modifier.height(24.dp))
        Button(onClick = onRequestPermissions) {
            Text("Grant Permissions")
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

        Spacer(modifier = Modifier.height(48.dp))

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
