import network
from config import load_dotenv

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
