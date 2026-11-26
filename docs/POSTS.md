# envspy — launch kit

Everything needed to put `envspy` in front of people. Copy-paste, but read the
"Before you post" section at the bottom first — it prevents the most common
self-post mistakes.

Repo: https://github.com/roma36637-alt/envspy

---

## 1. Publish the demo first

A recording beats any amount of prose. `docs/demo.cast` is a ready asciicast v2
file (~30 s: Python, Node, then `--check` failing).

`docs/demo.svg` is already rendered from that cast and embedded in the README,
so the repo looks finished **before** you upload anything anywhere. Regenerate
it after editing the cast with:

```bash
python docs/render_cast.py docs/demo.cast docs/demo.svg --max-lines=16
```

**Option A — upload the prepared file (fastest):**

1. Go to https://asciinema.org and sign in (GitHub login works).
2. *Upload* → pick `docs/demo.cast`.
3. Copy the recording URL, e.g. `https://asciinema.org/a/123456`.
4. Add this to the top of `README.md`, right under the one-liner:

   ```markdown
   [![asciicast](https://asciinema.org/a/123456.svg)](https://asciinema.org/a/123456)
   ```

**Option B — record it yourself (more authentic, shows your machine):**

```bash
# needs: asciinema, python3, node
bash docs/demo.sh                          # rehearse first
asciinema rec demo.cast -c "bash docs/demo.sh"
# then upload demo.cast at asciinema.org
```

**Option C — a GIF for X / Reddit** (they don't embed asciinema well):

```bash
# needs: asciinema, agg  (https://github.com/asciinema/agg)
asciinema rec demo.cast -c "bash docs/demo.sh"
agg demo.cast demo.gif --font-size 16
```

Post `demo.gif` directly in the Reddit post and attach it to the first X tweet.

---

## 2. Show HN

**Title** (HN strips leading "Show HN:" styling, keep it plain and factual):

> Show HN: envspy – Run a program to see which env vars it actually reads

**URL:** `https://github.com/roma36637-alt/envspy`

**First comment** (post it immediately after submitting — this is the text that
actually gets read):

> Every env-var tool I tried (dotenv linters, `grep -r getenv`, IDE plugins)
> guesses from source code. That breaks the moment a name is built at runtime:
>
> ```python
> prefix = "STRIPE"
> key = os.getenv(prefix + "_API_KEY")   # grep will never see STRIPE_API_KEY
> ```
>
> So envspy flips it around: it runs your command with a small hook installed
> and records every actual read.
>
> - Python: a `sitecustomize.py` that swaps `os.environ` for a recording subclass.
> - Node: a `--require` preload that wraps `process.env` in a `Proxy`.
> - It distinguishes `os.environ["X"]` (would raise KeyError), `os.getenv("X")`
>   and `os.getenv("X", "default")`.
> - It records **names and call sites only** — never values.
> - `envspy --check .env.example -- pytest` fails CI if your tests read a
>   variable your `.env.example` doesn't document.
>
> Honest limits: Python and Node only; it only sees code paths that actually
> run; bulk reads (`dict(os.environ)`) are ignored on purpose because otherwise
> every framework that copies the whole environment floods the report.
>
> It's 0.1.0 and I'd rather hear what breaks it than add features. What would
> you want it to do that it doesn't?

**Anticipated question — "why not just grep?"** (answer once, calmly):

> grep answers "which names appear in my source". It can't answer "which
> variables did this run depend on", which is what you need when a deploy works
> locally and dies in CI. Different question, different tool. I use grep too.

---

## 3. r/Python

**Title:**

> Every .env linter greps your code. I made one that runs it instead.

**Body:**

```markdown
I kept hitting the same bug: a service worked locally and failed in CI because
of a missing env var that no linter flagged — the name was assembled at runtime,
so `grep getenv` couldn't see it.

So I wrote `envspy`. Instead of scanning source, it runs your command with a
hook installed and reports what was *actually read*.

​```text
$ envspy -- python examples/demo.py

envspy  6 environment variable(s) read by `python examples/demo.py`

  · DATABASE_URL    unset    examples/demo.py:3
  · SECRET_KEY      unset    examples/demo.py:6
  · STRIPE_API_KEY  unset    examples/demo.py:10   ← built at runtime
  ~ DEBUG           default  examples/demo.py:4
  ~ PORT            default  examples/demo.py:5
  ~ TZ              default  examples/demo.py:7

  3 unset, 3 default. Values are never recorded.
​```

It separates four states:
- `✗ missing` — read with `os.environ["X"]`, would raise KeyError
- `· unset` — `os.getenv("X")`, no fallback
- `~ default` — `os.getenv("X", "d")` or `setdefault`
- `✓ set` — present when read

There's also a CI mode:

​```bash
envspy --check .env.example -- pytest
# exit 1 + the list of variables your code reads that .env.example doesn't document
​```

Only names and call sites are logged — values never touch the log file.

**Limitations, up front:**
- Python and Node only (a `getenv()` LD_PRELOAD hook for Go/Rust/C is next).
- Only sees code paths that execute — run it on your tests or a real session.
- Bulk reads (`dict(os.environ)`, `{...process.env}`) are deliberately ignored,
  so pydantic-settings-style loaders won't show per-variable reads.

Pure stdlib, Python 3.9+, `pip install -e .` from the repo. 6 tests, CI on
Linux/macOS/Windows × 3.9–3.13.

Repo: https://github.com/roma36637-alt/envspy

I'm mostly looking for holes in the approach — cases where it reports the wrong
thing or breaks a real app. Feedback very welcome.
```

> ⚠️ r/Python requires you to be an active community member and dislikes pure
> drive-by promotion. Post **one** time, reply to every comment, and don't
> cross-post the same day as r/node.

---

## 4. r/node

**Title:**

> I built a tool that shows which env vars a Node process actually reads

**Body:**

```markdown
`process.env.SOME_' + 'NAME` and `process.env[prefix + '_KEY']` are invisible to
grep-based env checkers. I wanted to know what a process *really* reads, so I
built `envspy` — it runs the command with a preload that wraps `process.env` in
a Proxy.

​```text
$ envspy -- node examples/demo.js

envspy  3 environment variable(s) read by `node examples/demo.js`

  · API_TOKEN     unset    examples/demo.js:3
  · DATABASE_URL  unset    examples/demo.js:2
  · PORT          unset    examples/demo.js:1
​```

Details that matter:
- Works via `NODE_OPTIONS=--require preload.js`, so child processes are covered.
- Only names + call sites are written; values are never read into the log.
- Bulk reads (`{...process.env}`, `Object.assign`) are ignored on purpose — they
  aren't "this variable matters", they're "copy everything".
- Node can't see fallbacks (`process.env.X || 3000`), so those show as `unset`.

The same binary also traces Python, which is handy in mixed repos. There's a
CI mode: `envspy --check .env.example -- npm test` exits 1 when the process
reads something you forgot to document.

Not on npm — it's a Python package (`pip install -e .`), since the orchestration
and the Python hook live there. Node support is the preload file, no deps.

Repo: https://github.com/roma36637-alt/envspy

Would love to hear which real-world Node setups break it (ESM-only? workers?
cluster?). Those are the cases I haven't tested enough.
```

---

## 5. X / Twitter thread

Attach `demo.gif` to tweet 1.

**1/**
> Every .env linter greps your code. All of them.
>
> That misses this:
>
> `prefix + "_API_KEY"`
>
> So I built envspy: it *runs* your program and shows which env vars it actually read.
>
> [gif]

**2/**
> It reports four states, not just "found / not found":
>
> ✗ missing → `os.environ["X"]`, would crash
> · unset → `os.getenv("X")`, no fallback
> ~ default → `os.getenv("X", "d")`
> ✓ set → present when read

**3/**
> Works for Python (swaps `os.environ`) and Node (Proxy over `process.env` via --require).
>
> Only variable NAMES and call sites are logged. Values never touch the file — so it's safe to run on prod-like config.

**4/**
> The CI trick I use most:
>
> `envspy --check .env.example -- pytest`
>
> Fails the build and lists exactly which vars your code reads that `.env.example` forgot to document.
>
> No more "works on my machine".

**5/**
> Honest limits: Python + Node only. Sees only code that runs. Ignores bulk copies of the whole env.
>
> v0.1.0, stdlib only, MIT.
>
> github.com/roma36637-alt/envspy
>
> Tell me what breaks it.

---

## 6. Title bank (mix and match)

Pick by channel; HN likes plain, Reddit likes a claim, X likes the hook.

- Every .env linter greps your code. I made one that runs it instead.
- Run your program, see which env vars it really reads.
- grep can't see `os.getenv(prefix + "_KEY")`. This can.
- The env var your code reads but `.env.example` forgot.
- Stop guessing env vars from source code.
- Your tests read 4 env vars. Does `.env.example` document them?
- `envspy`: env-var tracing, not env-var grepping.

---

## 7. Before you post (checklist)

- [ ] `docs/demo.cast` uploaded, its URL added to the README badge slot.
- [ ] README top is the one-liner + the `STRIPE_API_KEY` example (the hook).
- [ ] CI badge is green on `main` (it is: 5/5 jobs).
- [ ] Pin the release `v0.1.0`; link it in posts.
- [ ] Post **one** channel per day; reply to comments for the first few hours.
- [ ] In every post: state the limitations yourself. It reads as confidence,
      not weakness, and kills the top "but it doesn't do X" comment.
- [ ] Don't argue with "why not grep" — give the one-line answer and move on.
- [ ] If someone reports a real bug, fix + reply. That thread is your best ad.

## 8. What "success" looks like here

Small honest tools usually get their traction from **one** of these:

1. Someone hits your exact bug and posts your link in their team chat.
2. The `--check` CI idea gets copied into a popular repo's workflow.
3. A "why not just grep" thread where your answer is the top reply.

None of that needs stars on day one. Ship, answer questions, fix what breaks.