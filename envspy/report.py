from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

SCOPES = {
    "app": {"app"},
    "libs": {"app", "lib"},
    "all": {"app", "lib", "runtime"},
}

STATE_ORDER = {"missing": 0, "unset": 1, "default": 2, "set": 3}


def load_events(log_path: Path) -> list[dict]:
    events: list[dict] = []
    if not log_path.exists():
        return events
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and "k" in event:
            events.append(event)
    return events


def _relative(path: str, root: Path) -> str:
    try:
        return Path(path).resolve().relative_to(root).as_posix()
    except (ValueError, OSError):
        return path


def aggregate(events: list[dict], root: Path, scope: str, ignore: set[str]) -> list[dict]:
    allowed = SCOPES[scope]
    by_name: dict[str, list[dict]] = {}
    for event in events:
        if event.get("c") in allowed and event["k"] not in ignore:
            by_name.setdefault(event["k"], []).append(event)

    variables: list[dict] = []
    for name, group in by_name.items():
        missing = [e for e in group if not e.get("s")]
        if not missing:
            state = "set"
        elif any(e.get("m") == "required" for e in missing):
            state = "missing"  # read with os.environ["X"] while not set
        elif all(e.get("m") == "default" for e in missing):
            state = "default"  # not set, but the program has a fallback
        else:
            state = "unset"  # not set, read without a default
        locations: list[str] = []
        for event in group:
            loc = f"{_relative(event['f'], root)}:{event['l']}"
            if loc not in locations:
                locations.append(loc)
        variables.append({"name": name, "state": state, "locations": locations})

    variables.sort(key=lambda v: (STATE_ORDER[v["state"]], v["name"]))
    return variables


def render(variables: list[dict], command: list[str], *, color: bool, unicode: bool) -> str:
    icons = (
        {"missing": "✗", "unset": "·", "default": "~", "set": "✓"}
        if unicode
        else {"missing": "x", "unset": ".", "default": "~", "set": "+"}
    )
    paint = {"missing": "\033[91m", "unset": "\033[93m", "default": "\033[96m", "set": "\033[92m"}
    bold, dim, reset = ("\033[1m", "\033[2m", "\033[0m") if color else ("", "", "")

    title = " ".join(command)
    if not variables:
        return f"\n{bold}envspy{reset}  no environment variables were read by `{title}`\n"

    lines = ["", f"{bold}envspy{reset}  {len(variables)} environment variable(s) read by `{title}`", ""]
    width = max(len(v["name"]) for v in variables)
    for v in variables:
        tint = paint[v["state"]] if color else ""
        extra = len(v["locations"]) - 1
        where = v["locations"][0] + (f" (+{extra} more)" if extra > 0 else "")
        lines.append(
            f"  {tint}{icons[v['state']]}{reset} {v['name'].ljust(width)}  "
            f"{tint}{v['state'].ljust(7)}{reset}  {dim}{where}{reset}"
        )

    counts = Counter(v["state"] for v in variables)
    summary = ", ".join(f"{counts[s]} {s}" for s in STATE_ORDER if counts[s])
    lines += ["", f"  {dim}{summary}. Values are never recorded.{reset}", ""]
    return "\n".join(lines)