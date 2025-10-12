# bike-iot-tracker

## Installation

### Setup

Start by creating and activating the venv and installing deps:

```
source firmware/activate.sh
```

### Firmware

To set up the webrepl I followed the instructions
[here](https://docs.micropython.org/en/latest/esp8266/tutorial/repl.html).

Connect to the device with:

```
mpremote connect /dev/ttyACM0
```

Then run the webrepl setup wizard with:

```
>>> import webrepl_setup
```

After it is setup, you'll want to install the firmware via USB:

```
make push-local
```

That'll copy the firmware files to the device. The `boot.py` will setup the wifi
on boot, and enable the (now configured) WebREPL. From here, you can now push
firmware updates OTA to the device via:

```
make push
```
