# Firmware

MicroPython firmware for the ESP32-based bike IoT tracker.

## Quick Start

### 1. Setup Development Environment

Create and activate the Python virtual environment:

```bash
source firmware/activate.sh
```

This installs development tools including `mpremote` for device communication.

### 2. Configure Device

Create a `.env` file in the `firmware/` directory with your settings:

```bash
# WebREPL credentials
WEBREPL_PASSWORD=your_password
WEBREPL_IP=192.168.1.xxx
WEBREPL_PORT=8266

# Serial port for initial setup
SERIAL_PORT=/dev/ttyACM0

# WiFi credentials (copied to device as device.env)
WIFI_SSID=your_network
WIFI_PASSWORD=your_password
```

### 3. Initial Device Setup

**One-time setup via USB:**

1. Connect to the device:
   ```bash
   mpremote connect /dev/ttyACM0
   ```

2. Run the WebREPL setup wizard:
   ```python
   >>> import webrepl_setup
   ```
   Follow the prompts to enable WebREPL and set a password.

3. Push initial files to enable WebREPL:
   ```bash
   make push-local
   ```
   This copies the minimal files needed ([boot.py](src/boot.py), [config.py](src/config.py)) and creates required directories.

4. Reboot the device. It will now connect to WiFi and start WebREPL.

### 4. Development Workflow

Once WebREPL is configured, you can develop wirelessly:

```bash
# Push all source files over WebREPL
make push

# Connect to WebREPL REPL
make repl

# Connect to serial REPL (when USB connected)
make repl-local
```

## Project Structure

```
firmware/
├── src/              # MicroPython source code (copied to device)
│   ├── boot.py       # Runs on device boot, sets up WiFi and WebREPL
│   ├── config.py     # Device configuration
│   └── main.py       # Application entry point
├── 3rdparty/         # Vendored third-party dependencies
│   └── README.md     # Dependency management documentation
├── stubs/            # Type stubs for IDE support
├── Makefile          # Build and deployment commands
└── .env              # Local configuration (not committed)
```

## Managing Dependencies

Third-party dependencies are vendored in the [3rdparty/](3rdparty/) directory. See [3rdparty/README.md](3rdparty/README.md) for details on managing dependencies.

To update all dependencies:

```bash
make update-3rdparty
```

## Development Tools

- **mpremote**: Serial connection and file operations
- **WebREPL**: Over-the-air file transfers and REPL access
- Type checking with Pyright (configured in [pyrightconfig.json](pyrightconfig.json))

## See Also

- [TESTING.md](TESTING.md) - Testing procedures and tools
- [3rdparty/README.md](3rdparty/README.md) - Dependency management
- [CLAUDE.md](../CLAUDE.md) - System specification and design principles
