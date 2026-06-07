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

import streamlit as st

# Must be the first Streamlit call in this entry script (not in app.app import).
st.set_page_config(
    page_title="SAT",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state=280,
)
st.set_option("client.toolbarMode", "viewer")

from app.app import main

main()

