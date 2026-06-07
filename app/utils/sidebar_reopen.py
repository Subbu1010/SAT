"""Fallback control to reopen a collapsed Streamlit sidebar."""

from __future__ import annotations

import streamlit as st

_REOPEN_SCRIPT = """
<script>
(function () {
  const doc = document;
  const FAB_ID = "sat-sidebar-reopen-fab";

  function removeFab() {
    const existing = doc.getElementById(FAB_ID);
    if (existing) existing.remove();
  }

  function expandControl() {
    const host = doc.querySelector('[data-testid="stExpandSidebarButton"]');
    if (!host) return null;
    return host.querySelector("button") || host;
  }

  function sidebarIsCollapsed() {
    const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
    if (!sidebar) return false;
    if (sidebar.getAttribute("aria-expanded") === "false") return true;
    const style = window.getComputedStyle(sidebar);
    const width = sidebar.getBoundingClientRect().width;
    return width < 8 || style.transform.includes("translateX(-");
  }

  function clickExpand() {
    const button = expandControl();
    if (button) {
      button.click();
      return true;
    }
    return false;
  }

  function ensureFab() {
    const collapsed = sidebarIsCollapsed();
    const hasExpand = !!expandControl();

    if (!collapsed || hasExpand) {
      removeFab();
      return;
    }
    if (doc.getElementById(FAB_ID)) return;

    const button = doc.createElement("button");
    button.id = FAB_ID;
    button.type = "button";
    button.textContent = "☰ Open menu";
    button.style.cssText = [
      "position:fixed",
      "top:12px",
      "left:12px",
      "z-index:999999",
      "padding:10px 16px",
      "background:#2d7ff9",
      "color:#fff",
      "border:none",
      "border-radius:10px",
      "font-weight:600",
      "cursor:pointer",
      "box-shadow:0 4px 14px rgba(45,127,249,0.35)",
    ].join(";");
    button.addEventListener("click", clickExpand);
    doc.body.appendChild(button);
  }

  ensureFab();
  window.setInterval(ensureFab, 400);
  const observer = new MutationObserver(ensureFab);
  observer.observe(doc.body, {subtree: true, attributes: true, childList: true});
})();
</script>
"""


def inject_sidebar_reopen_fab() -> None:
    """Inject once per run from the sidebar so main content keeps a flush top edge."""
    st.html(_REOPEN_SCRIPT, unsafe_allow_javascript=True, width="content")
