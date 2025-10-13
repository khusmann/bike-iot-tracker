
include .env

PYTHON = .venv/bin/python
MPREMOTE = .venv/bin/mpremote

WEBREPL_CLI = $(PYTHON) 3rdparty/tools/webrepl_cli.py -p $(WEBREPL_PASSWORD)

SRC_DIR = src
THIRDPARTY_DEVICE_DIR = 3rdparty/device

# Find all Python files in src directory (frequently changing application code)
SRC_FILES := $(shell find -L $(SRC_DIR) -type f -name '*.py')

# Find all Python files in 3rdparty/device directory (libraries to push to device)
THIRDPARTY_FILES := $(shell find -L $(THIRDPARTY_DEVICE_DIR) -type f -name '*.py')

.PHONY: help repl push push-lib push-local repl-local update-3rdparty

help:
	@echo "Available commands:"
	@echo "  make repl            - Connect to WebREPL"
	@echo "  make push            - Push src files to device via WebREPL"
	@echo "  make push-lib        - Push 3rdparty files and device.env to device via WebREPL"
	@echo "  make push-local      - Push boot files to device via serial (for initial setup)"
	@echo "  make repl-local      - Connect to REPL via serial"
	@echo "  make update-3rdparty - Update all third-party dependencies"

.DEFAULT_GOAL := help

repl:
	$(WEBREPL_CLI) $(WEBREPL_IP):$(WEBREPL_PORT)

push:
	@for file in $(SRC_FILES); do \
		relative=$$(echo $$file | sed 's|^$(SRC_DIR)/||'); \
		echo "Pushing $$relative..."; \
		$(WEBREPL_CLI) $$file $(WEBREPL_IP):$(WEBREPL_PORT):$$relative; \
	done

push-lib:
	@echo "Pushing device.env..."
	@$(WEBREPL_CLI) .env $(WEBREPL_IP):$(WEBREPL_PORT):device.env
	@for file in $(THIRDPARTY_FILES); do \
		relative=$$(echo $$file | sed 's|^$(THIRDPARTY_DEVICE_DIR)/||'); \
		echo "Pushing $$relative..."; \
		$(WEBREPL_CLI) $$file $(WEBREPL_IP):$(WEBREPL_PORT):$$relative; \
	done

# Push enough to get the WebREPL running
push-local:
	$(MPREMOTE) connect $(SERIAL_PORT) fs cp .env :device.env
	$(MPREMOTE) connect $(SERIAL_PORT) fs cp $(SRC_DIR)/boot.py :boot.py
	$(MPREMOTE) connect $(SERIAL_PORT) fs cp $(SRC_DIR)/config.py :config.py

repl-local:
	$(MPREMOTE) repl $(SERIAL_PORT)

# Update all third-party dependencies
update-3rdparty:
	$(MAKE) -C 3rdparty update