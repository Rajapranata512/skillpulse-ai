from __future__ import annotations

import pytest

from skillpulse.release import public_runtime


def test_help_exits_without_starting_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        public_runtime,
        "run",
        lambda: pytest.fail("help must not start public listeners"),
    )

    with pytest.raises(SystemExit) as exit_info:
        public_runtime.main(["--help"])

    assert exit_info.value.code == 0
