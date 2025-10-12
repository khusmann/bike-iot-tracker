
include .env

PYTHON = .venv/bin/python
MPREMOTE = .venv/bin/mpremote

WEBREPL_CLI = $(PYTHON) 3rdparty/webrepl_cli.py -p $(WEBREPL_PASSWORD)

SRC_DIR = src

# Find all Python files in src directory recursively (following symlinks)
SRC_FILES := $(shell find -L $(SRC_DIR) -type f -name '*.py')

.PHONY: repl push push-local repl-local update-3rdparty

repl:
	$(WEBREPL_CLI) $(WEBREPL_IP):$(WEBREPL_PORT)

push:
	@$(WEBREPL_CLI) .env $(WEBREPL_IP):$(WEBREPL_PORT):device.env
	@for file in $(SRC_FILES); do \
		relative=$$(echo $$file | sed 's|^$(SRC_DIR)/||'); \
		echo "Pushing $$relative..."; \
		$(WEBREPL_CLI) $$file $(WEBREPL_IP):$(WEBREPL_PORT):$$relative; \
	done

# Push enough to get the WebREPL running
push-local:
	$(MPREMOTE) connect $(SERIAL_PORT) fs cp .env :device.env
	$(MPREMOTE) connect $(SERIAL_PORT) fs cp $(SRC_DIR)/boot.py :boot.py
	$(MPREMOTE) connect $(SERIAL_PORT) fs cp $(SRC_DIR)/config.py :config.py
	$(MPREMOTE) connect $(SERIAL_PORT) fs mkdir aioble

repl-local:
	$(MPREMOTE) repl $(SERIAL_PORT)

# Update all third-party dependencies
update-3rdparty:
	$(MAKE) -C 3rdparty update