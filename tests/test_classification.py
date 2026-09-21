from accessibility_map.analysis import classify_accessibility


def test_classify_good_medium_poor():
    assert classify_accessibility(1000, 1500, 3000) == "good"
    assert classify_accessibility(2500, 1500, 3000) == "medium"
    assert classify_accessibility(4500, 1500, 3000) == "poor"


def test_classify_missing_distance():
    assert classify_accessibility(None, 1500, 3000) == "unknown"
