import network
import time


def load_dotenv(filepath: str):
    env: dict[str, str] = {}
    try:
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, val = line.split('=', 1)
                    env[key.strip()] = val.strip()
    except OSError:
        print("No .env file found")
    return env


def connect_wifi(ssid: str, password: str, timeout: int = 15):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print(f"Connecting to Wi-Fi SSID: {ssid}")
        wlan.connect(ssid, password)
        start = time.time()
        while not wlan.isconnected():
            if time.time() - start > timeout:
                print("Wi-Fi connection timed out!")
                return False
            time.sleep(1)
    print("Connected with IP:", wlan.ifconfig()[0])
    return True


env = load_dotenv('.env')

ssid = env.get('WIFI_SSID')
password = env.get('WIFI_PASSWORD')

if ssid and password:
    connect_wifi(ssid, password)
else:
    print("SSID or PASSWORD not found in .env")

try:
    import webrepl
    webrepl.start()
except ImportError:
    print("WebREPL not available or not configured")
