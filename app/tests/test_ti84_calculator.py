from app.components.ti84_calculator import (
    FRAME_HEIGHT_PX,
    LAUNCHER_SIZE_PX,
    PANEL_WIDTH_PX,
    TI84_CALCULATOR_URL,
    TI84_PAGE_KEYS,
    _build_ti84_cleanup_script,
    _build_ti84_component_html,
    _launcher_id,
    is_ti84_allowed_page,
)
from app.components.ti84_icon import ti84_icon_html


def test_ti84_icon_is_svg_image():
    html = ti84_icon_html()
    assert html.startswith("<svg")
    assert "TI-84" in html


def test_ti84_component_uses_parent_document_bridge():
    html = _build_ti84_component_html(page_key="practice", open_on_load=False)

    assert "window.parent" in html
    assert _launcher_id("practice") in html
    assert str(LAUNCHER_SIZE_PX) in html
    assert "attachDragTarget" in html
    assert "pointermove" in html
    assert "setOpen(true)" in html
    assert TI84_CALCULATOR_URL in html


def test_ti84_component_uses_compact_panel_on_right():
    html = _build_ti84_component_html(page_key="mock_exam", open_on_load=True)

    assert str(PANEL_WIDTH_PX) in html
    assert str(FRAME_HEIGHT_PX) in html
    assert "defaultPanelPosition" in html
    assert "OPEN_ON_LOAD" in html
    assert "sat-ti84-zoom-bar" not in html


def test_ti84_cleanup_script_removes_launchers_and_modals():
    html = _build_ti84_cleanup_script(TI84_PAGE_KEYS)

    assert '"practice"' in html
    assert '"mock_exam"' in html
    assert "sat-ti84-launcher-" in html
    assert "sat-ti84-modal-" in html
    assert "sat-ti84-styles" in html
    assert "window.parent" in html


def test_is_ti84_allowed_page_matches_practice_and_mock_exam():
    assert is_ti84_allowed_page("http://localhost:8501/practice")
    assert is_ti84_allowed_page("http://localhost:8501/mock-exam")
    assert not is_ti84_allowed_page("http://localhost:8501/dashboard")
    assert not is_ti84_allowed_page("http://localhost:8501/")
