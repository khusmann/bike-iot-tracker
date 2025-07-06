
include ../.env

WEBREPL_CLI = ../3rdparty/webrepl_cli.py
PYTHON = ../.venv/bin/python
MPREMOTE = ../.venv/bin/mpremote

push:
	$(PYTHON) $(WEBREPL_CLI) -p $(WEBREPL_PASSWORD) boot.py $(WEBREPL_IP):boot.py
	$(PYTHON) $(WEBREPL_CLI) -p $(WEBREPL_PASSWORD) main.py $(WEBREPL_IP):main.py
	$(PYTHON) $(WEBREPL_CLI) -p $(WEBREPL_PASSWORD) ../.env $(WEBREPL_IP):device.env

push-local:
	$(MPREMOTE) connect $(SERIAL_PORT) fs cp boot.py :
	$(MPREMOTE) connect $(SERIAL_PORT) fs cp main.py :
	$(MPREMOTE) connect $(SERIAL_PORT) fs cp ../.env :.env
