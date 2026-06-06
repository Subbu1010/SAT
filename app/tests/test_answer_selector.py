from app.components.answer_selector import answer_from_widget


def test_answer_from_widget_index():
    options = ["Alpha", "Beta", "Gamma"]
    assert answer_from_widget(options, 1) == "Beta"


def test_answer_from_widget_legacy_text():
    options = ["Alpha", "Beta", "Gamma"]
    assert answer_from_widget(options, "Gamma") == "Gamma"


def test_answer_from_widget_empty():
    assert answer_from_widget(["A", "B"], None) is None
