#!/usr/bin/env python3
"""Render docs/demo.cast into a static SVG "terminal window" for the README.

Why a static SVG: GitHub renders it inline with no external hosting, unlike an
asciinema/GIF that needs a service. Re-run after editing the cast:

    python docs/render_cast.py docs/demo.cast docs/demo.svg

Whitespace is never emitted: every token is placed at an explicit column, so
columns line up no matter which monospace font the viewer uses.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ANSI = re.compile(r"(\x1b\[[0-9;]*m|\r\n|\r|\n)")

COLORS = {
    "93": "#e3b341",  # unset    (yellow)
    "96": "#56d4dd",  # default  (cyan)
    "91": "#f85149",  # missing  (red)
    "92": "#3fb950",  # set      (green)
    "31": "#f85149",
    "36": "#79c0ff",
    "39": "#c9d1d9",
}
DEFAULT_FG = "#c9d1d9"
DIM_FG = "#8b949e"

FONT_SIZE = 14
CHAR_W = 8.4
LINE_H = 21
PAD = 26
BAR_H = 40


def apply_sgr(state, codes):
    fg, bold, dim = state
    for code in codes.split(";"):
        if code in ("", "0"):
            fg, bold, dim = DEFAULT_FG, False, False
        elif code == "1":
            bold = True
        elif code == "2":
            dim = True
        elif code == "22":
            bold = dim = False
        elif code in COLORS:
            fg = COLORS[code]
    return (fg, bold, dim)


def build_lines(cast_text: str):
    first, *rest = cast_text.splitlines()
    header = json.loads(first)
    lines = [[]]
    state = (DEFAULT_FG, False, False)
    for raw in rest:
        if not raw.strip():
            continue
        _ts, kind, data = json.loads(raw)
        if kind != "o":
            continue
        for piece in ANSI.split(data):
            if not piece:
                continue
            if piece.startswith("\x1b["):
                state = apply_sgr(state, piece[2:-1])
            elif piece in ("\r\n", "\n"):
                lines.append([])
            elif piece == "\r":
                continue
            else:
                lines[-1].append((piece, state))
    while lines and not lines[-1]:
        lines.pop()
    return header, lines


def tokens(line):
    """Group non-space runs, keeping their starting column and style."""
    out, cur, col = [], None, 0
    for text, state in line:
        for ch in text:
            if ch == " ":
                if cur:
                    out.append(cur)
                    cur = None
                col += 1
            else:
                if cur is not None and cur["state"] == state:
                    cur["text"] += ch
                else:
                    if cur:
                        out.append(cur)
                    cur = {"text": ch, "state": state, "col": col}
                col += 1
    if cur:
        out.append(cur)
    return out, col


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def render(cast_path: Path, max_lines: int | None = None) -> str:
    header, lines = build_lines(cast_path.read_text(encoding="utf-8"))
    if max_lines:
        lines = lines[:max_lines]
    max_cols = max((tokens(line)[1] for line in lines), default=0)
    width = PAD * 2 + max_cols * CHAR_W
    height = BAR_H + PAD + len(lines) * LINE_H + PAD

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" '
        f'height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}" '
        f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
        f'<rect x="0.5" y="0.5" width="{width - 1:.0f}" height="{height - 1:.0f}" '
        f'rx="10" fill="#0d1117" stroke="#30363d"/>',
    ]
    # window chrome
    for i, color in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        out.append(
            f'<circle cx="{22 + i * 18}" cy="{BAR_H / 2:.0f}" r="6" fill="{color}"/>'
        )
    out.append(
        f'<text x="{width / 2:.0f}" y="{BAR_H / 2 + 4:.0f}" fill="#8b949e" '
        f'font-size="12" text-anchor="middle">envspy</text>'
    )
    out.append(
        f'<line x1="0" y1="{BAR_H}" x2="{width:.0f}" y2="{BAR_H}" stroke="#30363d"/>'
    )

    y = BAR_H + PAD + FONT_SIZE
    for line in lines:
        for tok in tokens(line)[0]:
            fg, bold, dim = tok["state"]
            color = DIM_FG if dim else fg
            weight = ' font-weight="700"' if bold and not dim else ""
            x = PAD + tok["col"] * CHAR_W
            out.append(
                f'<text x="{x:.1f}" y="{y:.0f}" fill="{color}" '
                f'font-size="{FONT_SIZE}"{weight}>{esc(tok["text"])}</text>'
            )
        y += LINE_H

    out.append("</svg>")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    max_lines = None
    for a in sys.argv[1:]:
        if a.startswith("--max-lines="):
            max_lines = int(a.split("=", 1)[1])

    src = Path(args[0] if len(args) > 0 else "docs/demo.cast")
    dst = Path(args[1] if len(args) > 1 else "docs/demo.svg")

    dst.write_text(render(src, max_lines=max_lines), encoding="utf-8")
    print(f"wrote {dst} ({dst.stat().st_size} bytes)")