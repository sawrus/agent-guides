from src import api


def test_app_exists():
    assert api.app is not None
