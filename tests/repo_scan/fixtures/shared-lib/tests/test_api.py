from shared_lib import api


def test_module_has_send():
    assert callable(api.send_application_context)
