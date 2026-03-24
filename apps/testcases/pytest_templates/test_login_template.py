import pytest

@pytest.mark.order(1)
def test_api_login(api_logined_data):
    """
    Login interface test case. 
    Runs first due to @pytest.mark.order(1).
    Populates api_logined_data with token and user info on success.
    """
    # Example logic (replace with actual platform request)
    # response = api_client.post("/api/login", json={"username": "test", "password": "123"})
    # assert response.status_code == 200
    # data = response.json()
    
    # Store data
    api_logined_data["token"] = "example_token_123"
    api_logined_data["username"] = "test_user"
    assert True

def test_dependent_feature(api_logined_data):
    """
    Subsequent test case dependent on login. 
    If login failed, api_logined_data won't have 'token', so we skip instead of fail.
    """
    try:
        token = api_logined_data["token"]
        username = api_logined_data["username"]
    except KeyError:
        pytest.skip("Login failed or didn't run, skipping dependent test case.")

    # Execute authorized API call
    # headers = {"Authorization": f"Bearer {token}"}
    # response = api_client.get("/api/feature", headers=headers)
    # assert response.status_code == 200
    assert token == "example_token_123"
