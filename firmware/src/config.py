# import typing as t


def load_dotenv(filepath: str = "device.env"):
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


class Config:
    wifi_ssid: str
    wifi_password: str

    def __init__(self, env: dict[str, str] = load_dotenv()):
        self.wifi_ssid = env["WIFI_SSID"]
        self.wifi_password = env["WIFI_PASSWORD"]
