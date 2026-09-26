from fastapi import status


def test_scenario_1_anonymous_access_unauthorized(client):
    """СЦЕНАРІЙ 1: Анонімний доступ повертає 401 Unauthorized."""
    # Запит до профілю без заголовка Authorization
    response_me = client.get("/api/v1/auth/me")
    assert response_me.status_code == status.HTTP_401_UNAUTHORIZED

    # Запит до панелі адміністратора без токена
    response_admin = client.get("/api/v1/admin/dashboard")
    assert response_admin.status_code == status.HTTP_401_UNAUTHORIZED

    # Запит до порталу ріпердока без токена
    response_vendor = client.get("/api/v1/vendor/portal")
    assert response_vendor.status_code == status.HTTP_401_UNAUTHORIZED

    # Спроба створення товару без токена
    response_create = client.post(
        "/api/v1/items/",
        json={
            "title": "Хакерський чіп",
            "slug": "hacker-chip",
            "category": "SOFTWARE",
            "price": 500.0,
        },
    )
    assert response_create.status_code == status.HTTP_401_UNAUTHORIZED


def test_scenario_2_authentication_and_login_validation(client, seed_users):
    """СЦЕНАРІЙ 2: Реєстрація, успішний вхід (200) та помилки автентифікації (401)."""
    # 1. Успішна реєстрація нового покупця
    reg_response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "blade_runner",
            "email": "deckard@runedrive.net",
            "password": "OrigamiSheep2026!",
            "role": "BUYER",
        },
    )
    assert reg_response.status_code == status.HTTP_201_CREATED
    data = reg_response.json()
    assert data["username"] == "blade_runner"
    assert data["role"] == "BUYER"
    assert "id" in data

    # 2. Заборона реєстрації адміністратора через відкритий API
    admin_reg_fail = client.post(
        "/api/v1/auth/register",
        json={
            "username": "fake_admin",
            "email": "fake_admin@runedrive.net",
            "password": "RootPassword123!",
            "role": "ADMIN",
        },
    )
    assert admin_reg_fail.status_code == status.HTTP_400_BAD_REQUEST

    # 3. Успішний вхід із правильними даними -> 200 OK + JWT токен
    login_success = client.post(
        "/api/v1/auth/login",
        json={"username": "street_samurai", "password": "SamuraiPass123!"},
    )
    assert login_success.status_code == status.HTTP_200_OK
    token_data = login_success.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["role"] == "BUYER"

    # 4. Вхід із неправильним паролем -> 401 Unauthorized
    login_wrong_pass = client.post(
        "/api/v1/auth/login",
        json={"username": "street_samurai", "password": "WrongPassword999!"},
    )
    assert login_wrong_pass.status_code == status.HTTP_401_UNAUTHORIZED

    # 5. Вхід неіснуючого користувача -> 401 Unauthorized
    login_non_existent = client.post(
        "/api/v1/auth/login",
        json={"username": "ghost_in_the_shell", "password": "SomePassword123!"},
    )
    assert login_non_existent.status_code == status.HTTP_401_UNAUTHORIZED


def test_scenario_3_vertical_role_escalation_rbac(client, seed_users):
    """СЦЕНАРІЙ 3: Вертикальне розмежування ролей (RBAC).

    Користувач ролі BUYER не має доступу до адмін-панелі (403 Forbidden).
    Адміністратор має повний доступ (200 OK).
    """
    buyer_token = seed_users["buyer1_token"]
    admin_token = seed_users["admin_token"]
    ripperdoc_token = seed_users["ripperdoc1_token"]

    # 1. Звичайний покупець лізе в панель адміністратора -> 403 Forbidden
    resp_buyer_to_admin = client.get(
        "/api/v1/admin/dashboard",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp_buyer_to_admin.status_code == status.HTTP_403_FORBIDDEN

    # 2. Звичайний покупець лізе в кабінет ріпердока -> 403 Forbidden
    resp_buyer_to_vendor = client.get(
        "/api/v1/vendor/portal",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp_buyer_to_vendor.status_code == status.HTTP_403_FORBIDDEN

    # 3. Звичайний покупець намагається створити товар у каталозі -> 403 Forbidden
    resp_buyer_create_item = client.post(
        "/api/v1/items/",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={
            "title": "Незаконна пушка",
            "slug": "illegal-gun",
            "category": "IMPLANT",
            "price": 9999.0,
        },
    )
    assert resp_buyer_create_item.status_code == status.HTTP_403_FORBIDDEN

    # 4. Адміністратор отримує доступ до панелі керування -> 200 OK
    resp_admin_dashboard = client.get(
        "/api/v1/admin/dashboard",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_admin_dashboard.status_code == status.HTTP_200_OK
    assert resp_admin_dashboard.json()["system_status"] == "OPERATIONAL"

    # 5. Ріпердок отримує доступ до свого порталу -> 200 OK
    resp_vendor_portal = client.get(
        "/api/v1/vendor/portal",
        headers={"Authorization": f"Bearer {ripperdoc_token}"},
    )
    assert resp_vendor_portal.status_code == status.HTTP_200_OK
    assert resp_vendor_portal.json()["clinic_status"] == "OPEN_FOR_IMPLANTATION"


def test_scenario_4_horizontal_idor_protection(client, seed_users):
    """СЦЕНАРІЙ 4: Горизонтальне розмежування прав (IDOR захист).

    1. Спроба користувача змінити чужий профіль повертає 403 Forbidden.
    2. Спроба ріпердока змінити/видалити чужий товар повертає 403 Forbidden.
    """
    buyer1_id = str(seed_users["buyer1"].id)
    buyer1_token = seed_users["buyer1_token"]

    buyer2_id = str(seed_users["buyer2"].id)
    admin_token = seed_users["admin_token"]

    item1_id = str(seed_users["item1"].id)
    ripperdoc1_token = seed_users["ripperdoc1_token"]
    ripperdoc2_token = seed_users["ripperdoc2_token"]

    # 1. IDOR профілю: Buyer 1 намагається змінити дані Buyer 2 -> 403 Forbidden
    resp_idor_user = client.patch(
        f"/api/v1/users/{buyer2_id}",
        headers={"Authorization": f"Bearer {buyer1_token}"},
        json={"username": "hacked_user"},
    )
    assert resp_idor_user.status_code == status.HTTP_403_FORBIDDEN
    assert "IDOR захист" in resp_idor_user.json()["detail"]

    # 2. Buyer 1 змінює свій власний профіль -> 200 OK
    resp_own_user = client.patch(
        f"/api/v1/users/{buyer1_id}",
        headers={"Authorization": f"Bearer {buyer1_token}"},
        json={"username": "street_samurai_updated"},
    )
    assert resp_own_user.status_code == status.HTTP_200_OK
    assert resp_own_user.json()["username"] == "street_samurai_updated"

    # 3. Адміністратор може оновити профіль будь-кого -> 200 OK
    resp_admin_override = client.patch(
        f"/api/v1/users/{buyer2_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"username": "cyber_mage_moderated"},
    )
    assert resp_admin_override.status_code == status.HTTP_200_OK

    # 4. IDOR товару: Ripperdoc 2 намагається змінити товар, що належить Ripperdoc 1 -> 403 Forbidden
    resp_idor_item = client.patch(
        f"/api/v1/items/{item1_id}",
        headers={"Authorization": f"Bearer {ripperdoc2_token}"},
        json={"price": 10.00},
    )
    assert resp_idor_item.status_code == status.HTTP_403_FORBIDDEN
    assert "IDOR захист" in resp_idor_item.json()["detail"]

    # 5. Ripperdoc 1 (власник) успішно змінює свій товар -> 200 OK
    resp_owner_item = client.patch(
        f"/api/v1/items/{item1_id}",
        headers={"Authorization": f"Bearer {ripperdoc1_token}"},
        json={"price": 1800.00},
    )
    assert resp_owner_item.status_code == status.HTTP_200_OK
    assert float(resp_owner_item.json()["price"]) == 1800.00
