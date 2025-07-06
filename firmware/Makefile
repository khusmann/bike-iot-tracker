
include ../.env

WEBREPL_CLI = ../3rdparty/webrepl_cli.py

push:
	python $(WEBREPL_CLI) -p $(WEBREPL_PASSWORD) boot.py $(DEVICE_IP):boot.py
	python $(WEBREPL_CLI) -p $(WEBREPL_PASSWORD) main.py $(DEVICE_IP):main.py
	python $(WEBREPL_CLI) -p $(WEBREPL_PASSWORD) ../.env $(DEVICE_IP):device.env

push-local:
	mpremote connect $(SERIAL_PORT) fs cp boot.py :
	mpremote connect $(SERIAL_PORT) fs cp main.py :
	mpremote connect $(SERIAL_PORT) fs cp ../.env :.env