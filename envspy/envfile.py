from __future__ import annotations

import re
from pathlib import Path

# "FOO=bar", "export FOO=bar" and commented-out "# FOO=bar" all count as documented.
_LINE = re.compile(r"^\s*#?\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")


def parse_names(path: Path) -> set[str]:
    names: set[str] = set()
    if not path.exists():
        return names
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = _LINE.match(line)
        if match:
            names.add(match.group(1))
    return names


def append_names(path: Path, names: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else "# Environment variables\n"
    block = "".join(f"{name}=\n" for name in names)
    path.write_text(existing.rstrip("\n") + "\n\n# Added by envspy\n" + block, encoding="utf-8")