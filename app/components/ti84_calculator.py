"""TI-84 calculator launcher beside batch metadata (draggable + in-page popup)."""

from __future__ import annotations

import json

import streamlit as st
import streamlit.components.v1 as components

from app.components.ti84_icon import ti84_icon_html
from app.utils.page_session import _url_matches_page
from app.utils.scoped_session import scoped_get, scoped_pop

TI84_CALCULATOR_URL = "https://ti84calculator.io/ti84calc.html"
TI84_PAGE_KEYS = ("practice", "mock_exam")

PANEL_WIDTH_PX = 308
HEADER_HEIGHT_PX = 34
FRAME_HEIGHT_PX = 660
DRAG_THRESHOLD_PX = 6
LAUNCHER_SIZE_PX = 40


def _launcher_id(page_key: str) -> str:
    return f"sat-ti84-launcher-{page_key}"


def _modal_id(page_key: str) -> str:
    return f"sat-ti84-modal-{page_key}"


def _current_url() -> str:
    return getattr(st.context, "url", "") or ""


def is_ti84_allowed_page(url: str | None = None) -> bool:
    """True when the current route is Practice or Mock Exam."""
    current = _current_url() if url is None else url
    return _url_matches_page(current, "practice") or _url_matches_page(current, "mock-exam")


def _build_ti84_cleanup_script(page_keys: tuple[str, ...]) -> str:
    keys_json = json.dumps(list(page_keys))
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8" /></head>
<body style="margin:0;padding:0;overflow:hidden;">
<script>
(function () {{
  const PAGE_KEYS = {keys_json};
  const doc = window.parent && window.parent.document
    ? window.parent.document
    : document;
  PAGE_KEYS.forEach((key) => {{
    doc.getElementById("sat-ti84-launcher-" + key)?.remove();
    doc.getElementById("sat-ti84-modal-" + key)?.remove();
  }});
  const hasCalculator = doc.querySelector(".sat-ti84-launcher, .sat-ti84-modal-host");
  if (!hasCalculator) {{
    doc.getElementById("sat-ti84-styles")?.remove();
  }}
}})();
</script>
</body>
</html>
"""


def inject_ti84_cleanup(page_keys: tuple[str, ...]) -> None:
    """Remove TI-84 launcher/modal DOM nodes for the given page keys."""
    if not page_keys:
        return
    components.html(
        _build_ti84_cleanup_script(page_keys),
        height=0,
        scrolling=False,
    )


def cleanup_ti84_on_disallowed_pages() -> None:
    """Hide calculator UI when the user navigates away from Practice/Mock Exam."""
    if is_ti84_allowed_page():
        return
    inject_ti84_cleanup(TI84_PAGE_KEYS)


def _build_ti84_component_html(*, page_key: str, open_on_load: bool) -> str:
    storage_open_key = f"sat-ti84-open:{page_key}"
    storage_launcher_pos_key = f"sat-ti84-launcher-pos:{page_key}"
    storage_panel_pos_key = f"sat-ti84-panel-pos:{page_key}"
    launcher_id = _launcher_id(page_key)
    modal_id = _modal_id(page_key)
    panel_id = f"sat-ti84-panel-{page_key}"

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8" /></head>
<body style="margin:0;padding:0;overflow:hidden;">
<script>
(function () {{
  const PAGE_KEY = {json.dumps(page_key)};
  const OPEN_ON_LOAD = {json.dumps(open_on_load)};
  const LAUNCHER_ID = {json.dumps(launcher_id)};
  const MODAL_ID = {json.dumps(modal_id)};
  const PANEL_ID = {json.dumps(panel_id)};
  const STORAGE_OPEN_KEY = {json.dumps(storage_open_key)};
  const STORAGE_LAUNCHER_POS_KEY = {json.dumps(storage_launcher_pos_key)};
  const STORAGE_PANEL_POS_KEY = {json.dumps(storage_panel_pos_key)};
  const CALC_URL = {json.dumps(TI84_CALCULATOR_URL)};
  const PANEL_WIDTH = {PANEL_WIDTH_PX};
  const HEADER_HEIGHT = {HEADER_HEIGHT_PX};
  const FRAME_HEIGHT = {FRAME_HEIGHT_PX};
  const PANEL_HEIGHT = HEADER_HEIGHT + FRAME_HEIGHT;
  const LAUNCHER_SIZE = {LAUNCHER_SIZE_PX};
  const DRAG_THRESHOLD = {DRAG_THRESHOLD_PX};
  const ICON_HTML = {json.dumps(ti84_icon_html())};

  const parentWin = window.parent;
  const doc = parentWin && parentWin.document ? parentWin.document : document;
  const frame = window.frameElement;

  function readSavedPosition(storageKey) {{
    try {{
      const raw = localStorage.getItem(storageKey);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (typeof parsed.left === "number" && typeof parsed.top === "number") return parsed;
    }} catch (err) {{}}
    return null;
  }}

  function savePosition(storageKey, left, top) {{
    try {{
      localStorage.setItem(storageKey, JSON.stringify({{ left, top, customized: true }}));
    }} catch (err) {{}}
  }}

  function clampPosition(left, top, width, height) {{
    return {{
      left: Math.min(Math.max(8, left), parentWin.innerWidth - width - 8),
      top: Math.min(Math.max(8, top), parentWin.innerHeight - height - 8),
    }};
  }}

  function placeElement(element, pos) {{
    element.style.left = `${{pos.left}}px`;
    element.style.top = `${{pos.top}}px`;
    element.style.right = "auto";
    element.style.bottom = "auto";
  }}

  function defaultPanelPosition() {{
    const top = Math.min(72, Math.max(12, parentWin.innerHeight - PANEL_HEIGHT - 16));
    return clampPosition(
      parentWin.innerWidth - PANEL_WIDTH - 18,
      top,
      PANEL_WIDTH,
      PANEL_HEIGHT
    );
  }}

  function frameAnchorPosition() {{
    if (!frame) return null;
    const rect = frame.getBoundingClientRect();
    return clampPosition(rect.left, rect.top, LAUNCHER_SIZE, LAUNCHER_SIZE);
  }}

  function ensureStyles() {{
    if (doc.getElementById("sat-ti84-styles")) return;
    const style = doc.createElement("style");
    style.id = "sat-ti84-styles";
    style.textContent = `
      .sat-ti84-launcher {{
        position: fixed;
        z-index: 999999;
        width: ${{LAUNCHER_SIZE}}px;
        height: ${{LAUNCHER_SIZE}}px;
        margin: 0;
        padding: 0;
        border: none;
        background: transparent;
        cursor: grab;
        user-select: none;
        touch-action: none;
        display: inline-flex;
        align-items: center;
        justify-content: center;
      }}
      .sat-ti84-launcher.dragging {{
        cursor: grabbing;
        filter: drop-shadow(0 8px 18px rgba(15, 23, 42, 0.28));
      }}
      .sat-ti84-launcher svg {{
        width: ${{LAUNCHER_SIZE}}px;
        height: ${{LAUNCHER_SIZE}}px;
        display: block;
        pointer-events: none;
      }}
      .sat-ti84-modal-host {{
        position: fixed;
        inset: 0;
        z-index: 999998;
        display: none;
        pointer-events: none;
      }}
      .sat-ti84-modal-host.open {{
        display: block;
      }}
      .sat-ti84-panel {{
        position: fixed;
        width: ${{PANEL_WIDTH}}px;
        height: ${{PANEL_HEIGHT}}px;
        background: #111827;
        border-radius: 12px;
        box-shadow: 0 14px 36px rgba(15, 23, 42, 0.28);
        overflow: hidden;
        display: flex;
        flex-direction: column;
        border: 1px solid rgba(148, 163, 184, 0.35);
        pointer-events: auto;
      }}
      .sat-ti84-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        height: ${{HEADER_HEIGHT}}px;
        padding: 0 10px;
        background: #0f172a;
        color: #f8fafc;
        font: 600 0.78rem/1.2 system-ui, -apple-system, Segoe UI, sans-serif;
        cursor: grab;
        user-select: none;
        touch-action: none;
      }}
      .sat-ti84-header.dragging {{ cursor: grabbing; }}
      .sat-ti84-close {{
        border: none;
        background: rgba(248, 250, 252, 0.12);
        color: #f8fafc;
        width: 26px;
        height: 26px;
        border-radius: 8px;
        cursor: pointer;
        font-size: 16px;
        line-height: 1;
      }}
      .sat-ti84-frame {{
        width: 100%;
        height: ${{FRAME_HEIGHT}}px;
        border: 0;
        background: #fff;
        display: block;
      }}
    `;
    doc.head.appendChild(style);
  }}

  function setOpen(isOpen) {{
    const modal = doc.getElementById(MODAL_ID);
    const launcher = doc.getElementById(LAUNCHER_ID);
    if (!modal) return;
    modal.classList.toggle("open", isOpen);
    modal.setAttribute("aria-hidden", isOpen ? "false" : "true");
    if (launcher) launcher.setAttribute("aria-expanded", isOpen ? "true" : "false");
    if (isOpen) syncPanelPosition();
  }}

  function attachDragTarget(target, handle, storageKey, onTap) {{
    if (!target || !handle || target.dataset.dragBound === "1") return;
    target.dataset.dragBound = "1";

    let session = null;

    function clearSession() {{
      if (!session) return;
      session = null;
      target.classList.remove("dragging");
      handle.classList.remove("dragging");
      doc.removeEventListener("pointermove", onMove);
      doc.removeEventListener("pointerup", onUp);
      doc.removeEventListener("pointercancel", onCancel);
    }}

    function onMove(event) {{
      if (!session) return;
      const deltaX = Math.abs(event.clientX - session.startX);
      const deltaY = Math.abs(event.clientY - session.startY);
      if (!session.moved && deltaX < DRAG_THRESHOLD && deltaY < DRAG_THRESHOLD) return;
      session.moved = true;
      const width = target.offsetWidth || (target.classList.contains("sat-ti84-panel") ? PANEL_WIDTH : LAUNCHER_SIZE);
      const height = target.offsetHeight || (target.classList.contains("sat-ti84-panel") ? PANEL_HEIGHT : LAUNCHER_SIZE);
      placeElement(
        target,
        clampPosition(
          event.clientX - session.offsetX,
          event.clientY - session.offsetY,
          width,
          height
        )
      );
    }}

    function onUp(event) {{
      if (!session) return;
      const moved = session.moved;
      const pointerId = session.pointerId;
      clearSession();
      try {{ handle.releasePointerCapture(pointerId); }} catch (err) {{}}
      const rect = target.getBoundingClientRect();
      savePosition(storageKey, rect.left, rect.top);
      if (moved) {{
        target.dataset.dragged = "1";
      }} else if (typeof onTap === "function") {{
        onTap();
      }}
    }}

    function onCancel() {{
      clearSession();
    }}

    handle.addEventListener("pointerdown", (event) => {{
      if (event.target.closest(".sat-ti84-close")) return;
      if (event.button !== 0) return;
      const rect = target.getBoundingClientRect();
      session = {{
        moved: false,
        startX: event.clientX,
        startY: event.clientY,
        offsetX: event.clientX - rect.left,
        offsetY: event.clientY - rect.top,
        pointerId: event.pointerId,
      }};
      target.classList.add("dragging");
      handle.classList.add("dragging");
      try {{ handle.setPointerCapture(event.pointerId); }} catch (err) {{}}
      doc.addEventListener("pointermove", onMove);
      doc.addEventListener("pointerup", onUp);
      doc.addEventListener("pointercancel", onCancel);
      event.preventDefault();
      event.stopPropagation();
    }});

    if (typeof onTap === "function") {{
      handle.addEventListener("click", (event) => {{
        if (target.dataset.dragged === "1") {{
          target.dataset.dragged = "0";
          event.preventDefault();
          return;
        }}
        event.preventDefault();
        onTap();
      }});
    }}
  }}

  function syncPanelPosition() {{
    const panel = doc.getElementById(PANEL_ID);
    if (!panel || panel.classList.contains("dragging")) return;
    const saved = readSavedPosition(STORAGE_PANEL_POS_KEY);
    if (saved?.customized) {{
      placeElement(panel, clampPosition(saved.left, saved.top, PANEL_WIDTH, PANEL_HEIGHT));
      return;
    }}
    placeElement(panel, defaultPanelPosition());
  }}

  function syncLauncherPosition() {{
    const launcher = doc.getElementById(LAUNCHER_ID);
    if (!launcher || launcher.classList.contains("dragging")) return;
    const saved = readSavedPosition(STORAGE_LAUNCHER_POS_KEY);
    if (saved?.customized) {{
      placeElement(
        launcher,
        clampPosition(saved.left, saved.top, LAUNCHER_SIZE, LAUNCHER_SIZE)
      );
      return;
    }}
    const anchored = frameAnchorPosition();
    if (anchored) placeElement(launcher, anchored);
  }}

  function buildModal() {{
    if (doc.getElementById(MODAL_ID)) return;
    const modal = doc.createElement("div");
    modal.id = MODAL_ID;
    modal.className = "sat-ti84-modal-host";
    modal.setAttribute("aria-hidden", "true");
    modal.innerHTML = `
      <div id="${{PANEL_ID}}" class="sat-ti84-panel" role="dialog" aria-label="TI-84 calculator">
        <div class="sat-ti84-header">
          <span>TI-84 Plus CE</span>
          <button class="sat-ti84-close" type="button" aria-label="Close calculator">×</button>
        </div>
        <iframe
          class="sat-ti84-frame"
          src="${{CALC_URL}}"
          title="TI-84 Plus CE calculator"
          loading="lazy"
          referrerpolicy="no-referrer-when-downgrade"
          allow="fullscreen"
        ></iframe>
      </div>
    `;
    modal.querySelector(".sat-ti84-close")?.addEventListener("click", () => setOpen(false));
    const panel = modal.querySelector(".sat-ti84-panel");
    const header = modal.querySelector(".sat-ti84-header");
    if (panel && header) attachDragTarget(panel, header, STORAGE_PANEL_POS_KEY, null);
    doc.body.appendChild(modal);
    syncPanelPosition();
  }}

  function buildLauncher() {{
    let launcher = doc.getElementById(LAUNCHER_ID);
    if (!launcher) {{
      launcher = doc.createElement("div");
      launcher.id = LAUNCHER_ID;
      launcher.className = "sat-ti84-launcher";
      launcher.title = "Drag to move · Click to open TI-84";
      launcher.setAttribute("role", "button");
      launcher.setAttribute("tabindex", "0");
      launcher.setAttribute("aria-label", "Open TI-84 calculator");
      launcher.setAttribute("aria-expanded", "false");
      launcher.innerHTML = ICON_HTML;
      doc.body.appendChild(launcher);
      attachDragTarget(launcher, launcher, STORAGE_LAUNCHER_POS_KEY, () => setOpen(true));
      launcher.addEventListener("keydown", (event) => {{
        if (event.key === "Enter" || event.key === " ") {{
          event.preventDefault();
          setOpen(true);
        }}
      }});
    }}
    syncLauncherPosition();
  }}

  function ensureTi84() {{
    ensureStyles();
    buildModal();
    buildLauncher();
    if (OPEN_ON_LOAD) setOpen(true);
  }}

  if (!doc.__satTi84EscapeBound) {{
    doc.addEventListener("keydown", (event) => {{
      if (event.key === "Escape") setOpen(false);
    }});
    parentWin.addEventListener("resize", () => {{
      syncLauncherPosition();
      syncPanelPosition();
    }});
    doc.__satTi84EscapeBound = true;
  }}

  ensureTi84();
}})();
</script>
</body>
</html>
"""


def render_ti84_batch_row(
    meta_text: str,
    *,
    page_key: str,
    show_calculator: bool,
    button_key: str,
) -> None:
    """Render batch metadata with a TI-84 image icon beside it."""
    del button_key

    if not show_calculator:
        st.caption(meta_text)
        inject_ti84_cleanup(TI84_PAGE_KEYS)
        return

    other_keys = tuple(key for key in TI84_PAGE_KEYS if key != page_key)
    if other_keys:
        inject_ti84_cleanup(other_keys)

    open_request_key = f"ti84_open_request_{page_key}"
    open_on_load = scoped_get(open_request_key, False)
    if open_on_load:
        scoped_pop(open_request_key, None)

    meta_col, ti84_col = st.columns([14, 1], vertical_alignment="center")
    with meta_col:
        st.caption(meta_text)
    with ti84_col:
        components.html(
            _build_ti84_component_html(page_key=page_key, open_on_load=open_on_load),
            height=LAUNCHER_SIZE_PX + 4,
            scrolling=False,
        )
