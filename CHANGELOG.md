# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-11-25

### Added

- Python hook: a `sitecustomize.py` that replaces `os.environ` with a recording
  subclass and logs variable names plus call sites (never values).
- Node.js hook: a `--require` preload that wraps `process.env` in a `Proxy`.
- Four read states: `missing` (`os.environ["X"]`, raises `KeyError`),
  `unset` (`os.getenv("X")`), `default` (`os.getenv("X", "d")` / `setdefault`)
  and `set`.
- Options: `--scope app|libs|all`, `--ignore VAR`, `--json FILE`, `--no-color`.
- `--check FILE`: exits with code 1 when the program reads variables that the
  file (e.g. `.env.example`) does not document.
- `--write FILE`: appends the variables that were read but not documented.
- Child processes inherit the hook.

### Fixed

- Support Python 3.14, where `os._Environ.__init__` takes five arguments
  instead of seven (3.9–3.13). The version is detected at runtime.
- `dict(os.environ)` was reported as reading every variable. Bulk copies are
  now detected via `keys()` and ignored.

[Unreleased]: https://github.com/roma36637-alt/envspy/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/roma36637-alt/envspy/releases/tag/v0.1.0
