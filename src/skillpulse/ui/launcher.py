"""Console launcher for the Streamlit portfolio app."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    try:
        from streamlit.web import cli as streamlit_cli
    except ImportError as error:
        raise RuntimeError('UI dependency missing. Install with: pip install -e ".[ui]"') from error
    app_path = Path(__file__).with_name("app.py")
    sys.argv = ["streamlit", "run", str(app_path), "--server.address=127.0.0.1"]
    raise SystemExit(streamlit_cli.main())


if __name__ == "__main__":
    main()
