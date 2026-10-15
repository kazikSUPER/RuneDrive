import os
import random

from locust import HttpUser, between, task

STAGED_LOAD_ENABLED = os.getenv("LOCUST_STAGED", "").strip().lower() in ("1", "true", "yes")


class RuneDriveBuyerUser(HttpUser):
    """
    Симуляція навантаження покупців на маркетплейс кібернетичних імплантів RuneDrive.
    Включає Scenario A (Read-Intensive), Scenario B (Write/Auth), Scenario C (Full Journey).
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
        """Scenario B: Write/Auth Intensive — валідація bcrypt та видача JWT."""
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
        """Scenario A: Read-Intensive — Високочастотний моніторинг стану (Health Check)."""
        self.client.get("/api/v1/health", name="[Core] GET /api/v1/health")

    @task(12)
    def test_get_catalog_items(self):
        """Scenario A: Read-Intensive — Перегляд каталогу товарів із кешуванням Redis."""
        resp = self.client.get("/api/v1/items", name="[Catalog] GET /api/v1/items")
        if resp.status_code == 200 and isinstance(resp.json(), list) and resp.json():
            self.item_ids = [item["id"] for item in resp.json() if "id" in item]

    @task(5)
    def test_get_item_details(self):
        """Scenario A: Read-Intensive — Перегляд картки конкретного товару за UUID."""
        if self.item_ids:
            item_id = random.choice(self.item_ids)
            self.client.get(
                f"/api/v1/items/{item_id}", name="[Catalog] GET /api/v1/items/[id]"
            )
        else:
            self.fetch_initial_items()

    @task(4)
    def test_get_current_user_profile(self):
        """Scenario C: Complex Workflow — Перевірка валідності сесії та прав користувача."""
        if self.auth_token:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            self.client.get(
                "/api/v1/auth/me",
                headers=headers,
                name="[Profile] GET /api/v1/auth/me",
            )
        else:
            self.authenticate()


if STAGED_LOAD_ENABLED:
    from locust.shape import LoadTestShape

    class StagedRampUpShape(LoadTestShape):
        """
        Warm-up + Staging Ramp-Up профіль навантаження (Лаб №5, п. 2.3).

        Етапи:
          1. Warm-up (5 VUs, 30с) — розігрів пулів з'єднань (asyncpg), DNS-кешу
             та прогрів Redis-кешу каталогу, щоб Cold Cache не спотворював заміри.
          2. Ступеневе нарощування 10 → 25 → 50 → 100 → 200 VUs — по 60с на ступінь,
             що дозволяє зафіксувати метрики (RPS, p50/p95/p99, Error Rate) на кожному рівні.
          3. Плавний спуск до 0 — коректне завершення прогону та фіналізація CSV-звітів.

        Активується лише при LOCUST_STAGED=1, інакше (за відсутності LoadShape)
        профіль керується аргументами CLI -u / -r.
        """

        stages = [
            {"duration": 30, "users": 5, "spawn_rate": 1},
            {"duration": 60, "users": 10, "spawn_rate": 5},
            {"duration": 60, "users": 25, "spawn_rate": 5},
            {"duration": 60, "users": 50, "spawn_rate": 5},
            {"duration": 60, "users": 100, "spawn_rate": 5},
            {"duration": 60, "users": 200, "spawn_rate": 10},
            {"duration": 10, "users": 0, "spawn_rate": 50},
        ]

        def tick(self):
            run_time = self.get_run_time()
            for stage in self.stages:
                if run_time < stage["duration"]:
                    return stage["users"], stage["spawn_rate"]
                run_time -= stage["duration"]
            return None
