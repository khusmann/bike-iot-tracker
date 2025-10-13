
include .env

PYTHON = .venv/bin/python
MPREMOTE = .venv/bin/mpremote

WEBREPL_CLI = $(PYTHON) 3rdparty/webrepl_cli.py -p $(WEBREPL_PASSWORD)

SRC_DIR = src

# Find all Python files in src directory recursively (following symlinks)
SRC_FILES := $(shell find -L $(SRC_DIR) -type f -name '*.py')

# Main source files to push separately (frequently changing), relative to $(SRC_DIR)
MAIN_FILES_REL := main.py utils.py

# Convert to full paths for filtering
MAIN_FILES := $(addprefix $(SRC_DIR)/,$(MAIN_FILES_REL))

# Filter out main files to get only library files
LIB_FILES := $(filter-out $(MAIN_FILES),$(SRC_FILES))

.PHONY: help repl push push-lib push-local repl-local update-3rdparty

help:
	@echo "Available commands:"
	@echo "  make repl            - Connect to WebREPL"
	@echo "  make push            - Push main.py to device via WebREPL"
	@echo "  make push-lib        - Push all supporting files (libs, config, etc.) to device via WebREPL"
	@echo "  make push-local      - Push boot files to device via serial (for initial setup)"
	@echo "  make repl-local      - Connect to REPL via serial"
	@echo "  make update-3rdparty - Update all third-party dependencies"

.DEFAULT_GOAL := help

repl:
	$(WEBREPL_CLI) $(WEBREPL_IP):$(WEBREPL_PORT)

push:
	@for file in $(MAIN_FILES); do \
		relative=$$(echo $$file | sed 's|^$(SRC_DIR)/||'); \
		echo "Pushing $$relative..."; \
		$(WEBREPL_CLI) $$file $(WEBREPL_IP):$(WEBREPL_PORT):$$relative; \
	done

push-lib:
	@echo "Pushing device.env..."
	@$(WEBREPL_CLI) .env $(WEBREPL_IP):$(WEBREPL_PORT):device.env
	@for file in $(LIB_FILES); do \
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