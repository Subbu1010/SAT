import site
import sys
from pathlib import Path


def _bootstrap_local_venv() -> None:
    """
    Ensure local .venv packages are available even if `streamlit` was launched
    from a global Python installation.
    """
    root = Path(__file__).resolve().parent
    venv_site = root / ".venv" / "Lib" / "site-packages"
    if venv_site.exists() and str(venv_site) not in sys.path:
        site.addsitedir(str(venv_site))


_bootstrap_local_venv()

from app.app import main


if __name__ == "__main__":
    # Delegate to the real app entrypoint inside the app package
    main()

