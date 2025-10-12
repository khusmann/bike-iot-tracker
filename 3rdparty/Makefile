# Read sources.txt and generate targets dynamically
FILES := $(shell grep -v '^\#' sources.txt | grep -v '^$$$$' | awk '{print $$1}')

.PHONY: update all $(FILES)

# Update all files
update: $(FILES)
	@echo "Done! All third-party dependencies updated."

# Update specific files (and make 'all' an alias for update)
all: update

# Generate a target for each file in sources.txt
$(FILES):
	@echo "Updating $@..."
	@url=$$(grep -v '^#' sources.txt | grep '^$@[[:space:]]' | awk '{print $$2}'); \
	if [ -z "$$url" ]; then \
		echo "Error: No URL found for $@ in sources.txt"; \
		exit 1; \
	fi; \
	curl -f -L -o "$@" "$$url" || { echo "Failed to download $@"; exit 1; }
