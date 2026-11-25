from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from envspy import __version__
from envspy.envfile import append_names, parse_names
from envspy.report import aggregate, load_events, render

HOOKS = Path(__file__).resolve().parent / "hooks"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="envspy",
        usage="envspy [options] -- COMMAND [ARGS...]",
        description="Run a command and report which environment variables it really reads.",
    )
    parser.add_argument(
        "-s", "--scope", choices=["app", "libs", "all"], default="app",
        help="app: your code only (default); libs: + site-packages/node_modules; all: + stdlib/runtime.",
    )
    parser.add_argument(
        "-i", "--ignore", action="append", default=[], metavar="VAR",
        help="Ignore a variable (can be repeated).",
    )
    parser.add_argument("--json", metavar="FILE", help="Also write the report as JSON to FILE.")
    parser.add_argument(
        "--check", metavar="FILE",
        help="Exit with 1 if the command read variables that FILE (e.g. .env.example) does not document.",
    )
    parser.add_argument(
        "--write", metavar="FILE",
        help="Append variables that were read but are not documented in FILE.",
    )
    parser.add_argument("--no-color", action="store_true", help="Disable colors.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def build_env(log: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["ENVSPY_LOG"] = str(log)

    python_hook = str(HOOKS / "python")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = python_hook + (os.pathsep + existing if existing else "")

    node_hook = f'--require "{(HOOKS / "node" / "preload.js").as_posix()}"'
    existing = env.get("NODE_OPTIONS")
    env["NODE_OPTIONS"] = f"{existing} {node_hook}" if existing else node_hook
    return env


def run_command(command: list[str], env: dict[str, str]) -> int:
    proc = subprocess.Popen(command, env=env)
    try:
        return proc.wait()
    except KeyboardInterrupt:
        try:
            return proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.terminate()
            return proc.wait()


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()

    if "--" in argv:
        split = argv.index("--")
        own, command = argv[:split], argv[split + 1:]
    else:
        own, command = argv, []

    args = parser.parse_args(own)
    if not command:
        parser.error("no command given. Usage: envspy [options] -- COMMAND [ARGS...]")

    color = not args.no_color and "NO_COLOR" not in os.environ and sys.stderr.isatty()
    if color and os.name == "nt":
        os.system("")  # enables ANSI escapes in Windows terminals
    unicode = "utf" in (getattr(sys.stderr, "encoding", None) or "").lower()

    with tempfile.TemporaryDirectory(prefix="envspy-") as tmp:
        log = Path(tmp) / "events.jsonl"
        log.touch()
        env = build_env(log)

        executable = shutil.which(command[0], path=env.get("PATH"))
        if executable is None:
            print(f"envspy: command not found: {command[0]}", file=sys.stderr)
            return 127

        exit_code = run_command([executable, *command[1:]], env)
        events = load_events(log)

    root = Path.cwd().resolve()
    variables = aggregate(events, root, args.scope, set(args.ignore))

    # The report goes to stderr so the program's own stdout stays pipeable.
    print(render(variables, command, color=color, unicode=unicode), file=sys.stderr)

    if args.json:
        payload = {"command": command, "exit_code": exit_code, "variables": variables}
        Path(args.json).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.write:
        target = Path(args.write)
        documented = parse_names(target)
        new = [v["name"] for v in variables if v["name"] not in documented]
        if new:
            append_names(target, new)
            print(f"envspy: added {len(new)} variable(s) to {target}", file=sys.stderr)
        else:
            print(f"envspy: {target} already documents everything that was read", file=sys.stderr)

    if args.check:
        target = Path(args.check)
        documented = parse_names(target)
        undocumented = [v["name"] for v in variables if v["name"] not in documented]
        if undocumented:
            print(f"envspy: read by the program but missing from {target}:", file=sys.stderr)
            for name in undocumented:
                print(f"  + {name}", file=sys.stderr)
            if exit_code == 0:
                exit_code = 1
        else:
            print(f"envspy: {target} documents every variable that was read", file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())