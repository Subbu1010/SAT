from app.services.adaptive_engine import next_difficulty


def test_increase_after_three_correct():
    assert next_difficulty([True, True, True], "Medium") == "Hard"


def test_decrease_after_three_wrong():
    assert next_difficulty([False, False, False], "Medium") == "Easy"
