import os
import network
from env import load_dotenv

# Turn on interface
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# Load config
env = load_dotenv()
ssid = env.get('WIFI_SSID')
password = env.get('WIFI_PASSWORD')

# Connect to Wifi
if ssid and password:
    wlan.connect(ssid, password)
else:
    if not ssid:
        print("WIFI_SSID not found in device.env")
    if not password:
        print("WIFI_PASSWORD not found in device.env")

# Enable webrepl
try:
    import webrepl
    webrepl.start()
except ImportError:
    print("WebREPL not available or not configured")

# Create necessary directories
folders_to_create = ['aioble', 'udataclasses', 'primitives']
for folder in folders_to_create:
    try:
        os.mkdir(folder)
        print(f"Created folder: {folder}")
    except OSError:
        pass  # Folder already exists
