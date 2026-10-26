from rule_catalog.app import rules


def test_rules():
    assert rules()[0]["name"] == "velocity"
