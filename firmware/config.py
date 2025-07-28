

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
