def test_register_and_login(client):
    # 1. Register a new user
    res = client.post(
        "/auth/register",
        json={"username": "testoperator", "password": "securepassword123", "role": "operator"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["username"] == "testoperator"

    # 2. Prevent duplicate registration
    res_dup = client.post(
        "/auth/register",
        json={"username": "testoperator", "password": "securepassword123"},
    )
    assert res_dup.status_code == 409

    # 3. Login with correct credentials
    login_res = client.post(
        "/auth/login",
        json={"username": "testoperator", "password": "securepassword123"},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # 4. Access /auth/me with Bearer token
    me_res = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["authenticated"] is True
    assert me_res.json()["username"] == "testoperator"

    # 5. Bad password login
    bad_login = client.post(
        "/auth/login",
        json={"username": "testoperator", "password": "wrongpassword"},
    )
    assert bad_login.status_code == 401
