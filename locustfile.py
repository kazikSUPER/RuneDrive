import random

from locust import HttpUser, between, task


class RuneDriveBuyerUser(HttpUser):
    """
    Симуляція навантаження покупців на маркетплейс кібернетичних імплантів RuneDrive.
    """

    wait_time = between(0.1, 0.5)

    def on_start(self):
        """Ініціалізація та авторизація через JSON-ендпоінт."""
        self.auth_token = None
        self.item_ids = []
        self.login_users = [
            {"username": "street_samurai", "password": "SamuraiPass123!"},
            {"username": "netrunner_admin", "password": "AdminSecret2026!"},
            {"username": "dr_viktor", "password": "ViktorRipperPass1!"},
        ]
        self.authenticate()
        self.fetch_initial_items()

    def authenticate(self):
        user = random.choice(self.login_users)
        resp = self.client.post(
            "/api/v1/auth/login",
            json=user,
            name="[Auth] POST /api/v1/auth/login",
        )
        if resp.status_code == 200:
            self.auth_token = resp.json().get("access_token")

    def fetch_initial_items(self):
        resp = self.client.get("/api/v1/items", name="[Catalog] GET /api/v1/items")
        if resp.status_code == 200 and isinstance(resp.json(), list):
            self.item_ids = [item["id"] for item in resp.json() if "id" in item]

    @task(6)
    def test_health_check(self):
        """Високочастотний моніторинг стану (Health Check)."""
        self.client.get("/api/v1/health", name="[Core] GET /api/v1/health")

    @task(12)
    def test_get_catalog_items(self):
        """Перегляд каталогу товарів."""
        resp = self.client.get("/api/v1/items", name="[Catalog] GET /api/v1/items")
        if resp.status_code == 200 and isinstance(resp.json(), list) and resp.json():
            self.item_ids = [item["id"] for item in resp.json() if "id" in item]

    @task(5)
    def test_get_item_details(self):
        """Перегляд конкретного товару за UUID."""
        if self.item_ids:
            item_id = random.choice(self.item_ids)
            self.client.get(
                f"/api/v1/items/{item_id}", name="[Catalog] GET /api/v1/items/[id]"
            )
        else:
            self.fetch_initial_items()

    @task(4)
    def test_get_current_user_profile(self):
        """Отримання власного профілю користувача."""
        if self.auth_token:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            self.client.get(
                "/api/v1/auth/me",
                headers=headers,
                name="[Profile] GET /api/v1/auth/me",
            )
        else:
            self.authenticate()
