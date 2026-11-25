# envspy

**Run any command and see which environment variables it *really* reads.**

Every other tool guesses env vars by grepping your source. `envspy` runs your program and watches.

```text
$ envspy -- python examples/demo.py

envspy  6 environment variable(s) read by `python examples/demo.py`

  · DATABASE_URL    unset    examples/demo.py:3
  · SECRET_KEY      unset    examples/demo.py:6
  · STRIPE_API_KEY  unset    examples/demo.py:10
  ~ DEBUG           default  examples/demo.py:4
  ~ PORT            default  examples/demo.py:5
  ~ TZ              default  examples/demo.py:7

  3 unset, 3 default. Values are never recorded.
```

Note `STRIPE_API_KEY`: the code builds the name at runtime (`prefix + "_API_KEY"`). A regex scanner can't see it, `envspy` can.

## Install

```bash
# from a checkout (works today)
pip install -e .

# once published to PyPI
# pip install envspy
```

No dependencies. Works with **Python** and **Node.js** programs.

## Usage

```bash
envspy -- python app.py              # any Python command
envspy -- node server.js             # any Node command
envspy -- pytest                     # audit what your test suite reads
envspy -- flask run                  # long-running? Ctrl-C prints the report

envspy --scope libs -- python app.py # also show reads made by dependencies
envspy --json report.json -- ...     # machine-readable report
envspy -i PATH -i HOME -- ...        # ignore variables
```

### Keep `.env.example` honest (CI)

```bash
# Fail if the program reads a variable that .env.example doesn't document
envspy --check .env.example -- pytest

# Or add the missing ones automatically
envspy --write .env.example -- pytest
```

```yaml
- run: pip install envspy
- run: envspy --check .env.example -- pytest
```

## States

| State | Meaning |
|---|---|
| `✓ set` | the variable was set when read |
| `~ default` | not set, but the program supplied a fallback (`os.getenv("X", "d")`, `setdefault`) |
| `· unset` | not set, read without a fallback (`os.getenv("X")` returns `None`) |
| `✗ missing` | not set and read with `os.environ["X"]` (raises `KeyError`) |

Node can't see fallbacks (`process.env.X || "d"`), so unset variables show as `unset` there.

## How it works

- **Python:** `envspy` puts a `sitecustomize.py` on `PYTHONPATH` that replaces `os.environ` with a recording subclass.
- **Node.js:** `envspy` adds a `--require` preload via `NODE_OPTIONS` that wraps `process.env` in a `Proxy`.
- Child processes inherit the hook, so subprocesses are covered as well.
- Only variable **names** and call sites are written to a temp file. Values are never read into the log.

## Limitations (honest list)

- It only sees code paths that actually run. Run it on your tests or a realistic session.
- Bulk reads (`dict(os.environ)`, `{...process.env}`, iterating all vars) are ignored on purpose. Frameworks that load the whole environment at once (e.g. pydantic-settings) won't show per-variable reads.
- Python and Node only for now. No Go/Rust/Ruby/Java yet.
- Frontend bundles that inline env at build time (`process.env.X` replaced by webpack/Vite) are only visible if you run the build under `envspy`.

## Roadmap

- [ ] `LD_PRELOAD` hook for `getenv()` (Go, Rust, C, Ruby, ...)
- [ ] `--diff` between two runs
- [ ] Deno / Bun

## Development

```bash
pip install -e . pytest
pytest
```

## License

MIT