# 3rdparty

This directory contains vendored third-party dependencies for the MicroPython
firmware.

## Managing Dependencies

Dependencies are configured in `sources.txt` with the format:

```
filename url
```

### Update All Dependencies

To update all third-party files to their pinned versions:

```bash
make update
```

### Update Individual Dependencies

To update a specific file only:

```bash
make <filename>          # e.g., make typing.py
```

This is useful when you want to:

- Update a single dependency to a new version (update the URL in `sources.txt`,
  then run `make <filename>`)
- Re-download a single file if it was accidentally modified
- Test changes to one dependency without affecting others

### Adding New Dependencies

1. Add a new line to `sources.txt` with the filename and URL
2. Run `make update` to download the file

### Updating to New Versions

To update a dependency to a newer version:

1. Update the URL in `sources.txt` to point to the new commit/version
2. Run `make <filename>` to fetch the updated file

## Current Dependencies

### webrepl_cli.py

CLI tool for WebREPL file operations and REPL access.

- **Source Repository**: https://github.com/micropython/webrepl

### typing.py

MicroPython typing stub for type hints compatibility.

- **Source Repository**: https://github.com/Josverl/micropython-stubs
