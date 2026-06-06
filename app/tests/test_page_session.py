from app.utils.page_session import _url_matches_page


def test_url_matches_practice_page():
    assert _url_matches_page("http://localhost:8501/practice", "practice")
    assert _url_matches_page("http://localhost:8501/practice?foo=1", "practice")
    assert not _url_matches_page("http://localhost:8501/mock-exam", "practice")
