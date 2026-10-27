from catalog_lib.app import rules


def test_rules():
    assert rules()[0]["name"] == "velocity"
