import pytest

@pytest.fixture(scope="session")
def api_logined_data():
    """
    Store token and username after login, shared across the entire test session.
    Populated by the login test case (which should run first).
    """
    return {}
