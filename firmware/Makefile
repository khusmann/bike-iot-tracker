
include ../.env

PYTHON = ../.venv/bin/python
MPREMOTE = ../.venv/bin/mpremote

WEBREPL_CLI = $(PYTHON) ../3rdparty/webrepl_cli.py -p $(WEBREPL_PASSWORD)

FILES = boot.py main.py config.py typing.py

repl:
	$(WEBREPL_CLI) $(WEBREPL_IP):$(WEBREPL_PORT)

push:
	@$(WEBREPL_CLI) ../.env $(WEBREPL_IP):$(WEBREPL_PORT):device.env
	@for file in $(FILES); do \
		echo; \
		$(WEBREPL_CLI) $$file $(WEBREPL_IP):$(WEBREPL_PORT):$$file; \
	done

# Push enough to get the WebREPL running
push-local:
	$(MPREMOTE) connect $(SERIAL_PORT) fs cp ../.env :device.env
	$(MPREMOTE) connect $(SERIAL_PORT) fs cp boot.py :
	$(MPREMOTE) connect $(SERIAL_PORT) fs cp config.py :

repl-local:
	$(MPREMOTE) repl $(SERIAL_PORT)