# Third-party dependencies management

# Third-party dependency files from sources.txt
THIRDPARTY_FILES := $(shell grep -v '^\#' sources.txt | grep -v '^$$' | awk '{print $$1}')

.PHONY: update $(THIRDPARTY_FILES)

# Update all third-party dependencies
update: $(THIRDPARTY_FILES)
	@echo "Done! All third-party dependencies updated."

# Generate a target for each file in sources.txt
$(THIRDPARTY_FILES):
	@echo "Updating $@..."
	@mkdir -p $$(dirname $@); \
	url=$$(grep -v '^#' sources.txt | awk '$$1 == "$@" {print $$2}'); \
	if [ -z "$$url" ]; then \
		echo "Error: No URL found for $@ in sources.txt"; \
		exit 1; \
	fi; \
	curl -f -L -o "$@" "$$url" || { echo "Failed to download $@"; exit 1; }
