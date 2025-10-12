
include ../.env

PYTHON = ../.venv/bin/python
MPREMOTE = ../.venv/bin/mpremote

WEBREPL_CLI = $(PYTHON) 3rdparty/webrepl_cli.py -p $(WEBREPL_PASSWORD)

FILES = boot.py main.py config.py typing.py

# Third-party dependency files from sources.txt
THIRDPARTY_FILES := $(shell grep -v '^\#' 3rdparty/sources.txt | grep -v '^$$$$' | awk '{print "3rdparty/" $$1}')

.PHONY: repl push push-local repl-local update-3rdparty $(THIRDPARTY_FILES)

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

# Update all third-party dependencies
update-3rdparty: $(THIRDPARTY_FILES)
	@echo "Done! All third-party dependencies updated."

# Generate a target for each file in 3rdparty/sources.txt
$(THIRDPARTY_FILES):
	@echo "Updating $@..."
	@mkdir -p $$(dirname $@); \
	relpath=$$(echo $@ | sed 's|^3rdparty/||'); \
	url=$$(grep -v '^#' 3rdparty/sources.txt | grep "^$$relpath[[:space:]]" | awk '{print $$2}'); \
	if [ -z "$$url" ]; then \
		echo "Error: No URL found for $$relpath in 3rdparty/sources.txt"; \
		exit 1; \
	fi; \
	curl -f -L -o "$@" "$$url" || { echo "Failed to download $@"; exit 1; }