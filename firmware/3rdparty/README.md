# 3rdparty

This directory contains vendored third-party code organized into:

- **`device/`** - Libraries that are pushed to the ESP32 device
- **`tools/`** - Host-side tools used during development

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

### Device Libraries (`device/`)

#### typing.py

MicroPython typing stub for type hints compatibility. Enables IDE support for Python type annotations in MicroPython code.

- **Source Repository**: https://github.com/Josverl/micropython-stubs

#### aioble

Async Bluetooth Low Energy library for MicroPython. Provides the core BLE functionality for the bike tracker.

- **Source Repository**: https://github.com/micropython/micropython-lib
- **Package**: `micropython/bluetooth/aioble`
- **Modules**: `__init__.py`, `core.py`, `device.py`, `server.py`, `peripheral.py`

#### udataclasses

MicroPython port of Python's dataclasses. Enables immutable data structures with type hints, aligned with the functional programming style.

- **Source Repository**: https://github.com/dhrosa/udataclasses
- **Modules**: Full package including `__init__.py`, `constants.py`, `decorator.py`, `field.py`, `functions.py`, `source.py`, `transform_spec.py`

#### primitives

Async primitives for MicroPython. Provides utilities for async programming patterns.

- **Source Repository**: https://github.com/peterhinch/micropython-async
- **Modules**: `__init__.py`, `pushbutton.py`, `delay_ms.py`

### Host Tools (`tools/`)

#### webrepl_cli.py

CLI tool for WebREPL file operations and REPL access. Used by the parent Makefile for over-the-air firmware updates.

- **Source Repository**: https://github.com/micropython/webrepl
