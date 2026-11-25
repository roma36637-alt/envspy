from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

from envspy.cli import main
from envspy.envfile import append_names, parse_names

PY_SCRIPT = """
import os
os.getenv("SPY_SET")
os.getenv("SPY_PLAIN")
os.getenv("SPY_DEFAULT", "x")
"SPY_CHECK" in os.environ
os.environ.setdefault("SPY_SETDEFAULT", "1")
try:
    os.environ["SPY_REQUIRED"]
except KeyError:
    pass
dict(os.environ)  # bulk copy: must not be reported
"""


def _states(report_path: Path) -> dict[str, str]:
    data = json.loads(report_path.read_text(encoding="utf-8"))
    return {v["name"]: v["state"] for v in data["variables"]}


def test_python_hook(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SPY_SET", "1")
    for name in ("SPY_PLAIN", "SPY_DEFAULT", "SPY_CHECK", "SPY_SETDEFAULT", "SPY_REQUIRED"):
        monkeypatch.delenv(name, raising=False)
    (tmp_path / "app.py").write_text(PY_SCRIPT, encoding="utf-8")

    code = main(["--json", "report.json", "--", sys.executable, "app.py"])

    assert code == 0
    assert _states(tmp_path / "report.json") == {
        "SPY_SET": "set",
        "SPY_PLAIN": "unset",
        "SPY_DEFAULT": "default",
        "SPY_CHECK": "unset",
        "SPY_SETDEFAULT": "default",
        "SPY_REQUIRED": "missing",
    }
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["variables"][-1]["locations"][0].startswith("app.py:")


def test_exit_code_is_propagated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text("raise SystemExit(3)\n", encoding="utf-8")
    assert main(["--", sys.executable, "app.py"]) == 3


def test_check_and_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SPY_DOC", "1")
    monkeypatch.delenv("SPY_NEW", raising=False)
    (tmp_path / "app.py").write_text(
        'import os\nos.getenv("SPY_DOC")\nos.getenv("SPY_NEW")\n', encoding="utf-8"
    )
    example = tmp_path / ".env.example"
    example.write_text("SPY_DOC=\n", encoding="utf-8")
    cmd = ["--", sys.executable, "app.py"]

    assert main(["--check", ".env.example", *cmd]) == 1
    assert main(["--write", ".env.example", *cmd]) == 0
    assert "SPY_NEW=" in example.read_text(encoding="utf-8")
    assert main(["--check", ".env.example", *cmd]) == 0


def test_command_not_found(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--", "definitely-not-a-real-command-xyz"]) == 127


def test_env_file_helpers(tmp_path: Path) -> None:
    path = tmp_path / ".env.example"
    path.write_text("A=1\nexport B=2\n# C=3\n# just a comment\n", encoding="utf-8")
    assert parse_names(path) == {"A", "B", "C"}
    append_names(path, ["D"])
    assert "D=" in path.read_text(encoding="utf-8")


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_node_hook(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SPY_NODE_SET", "1")
    monkeypatch.delenv("SPY_NODE_UNSET", raising=False)
    monkeypatch.delenv("SPY_NODE_HAS", raising=False)
    (tmp_path / "app.js").write_text(
        "process.env.SPY_NODE_SET;\n"
        "process.env.SPY_NODE_UNSET;\n"
        "'SPY_NODE_HAS' in process.env;\n"
        "const copy = { ...process.env };\n",
        encoding="utf-8",
    )

    code = main(["--json", "report.json", "--", "node", "app.js"])

    assert code == 0
    assert _states(tmp_path / "report.json") == {
        "SPY_NODE_SET": "set",
        "SPY_NODE_UNSET": "unset",
        "SPY_NODE_HAS": "unset",
    }