import sys
import time
import uuid

import requests

BASE_URL = "http://localhost:8080"


def run_cache_verification():
    print("=" * 75)
    print("  ТЕСТУВАННЯ РОЗПОДІЛЕНОГО КЕШУВАННЯ (LAB 4 - DISTRIBUTED CACHING)")
    print("  Патерни: Cache-Aside, Lazy Loading, Write-Invalidation, Graceful Fallback")
    print("=" * 75)

    session = requests.Session()

    print("\n[Крок 1] Перевірка доступності точки входу (Nginx Load Balancer)...")
    try:
        r = session.get(f"{BASE_URL}/api/v1/health", timeout=5)
        print(
            f"  Статус HTTP {r.status_code} | Обслуговував інстанс: [{r.headers.get('X-Instance-ID', 'unknown')}]"
        )
    except Exception as e:
        print(f"  [Помилка підключення]: {e}")
        print("  Будь ласка, запустіть сервіси через: docker compose up -d")
        sys.exit(1)

    print("\n[Крок 2] Холодний запит каталогу (Cache MISS / Primary Database Read)...")
    start_t = time.perf_counter()
    resp_miss = session.get(f"{BASE_URL}/api/v1/items/?skip=0&limit=10")
    cold_duration_ms = (time.perf_counter() - start_t) * 1000

    cache_header = resp_miss.headers.get("X-Cache", "NONE")
    inst = resp_miss.headers.get("X-Instance-ID", "unknown")
    print(
        f"  HTTP {resp_miss.status_code} | Час: {cold_duration_ms:.2f} ms | X-Cache: [{cache_header}] | Інстанс: [{inst}]"
    )

    if resp_miss.status_code != 200:
        print(f"  [Помилка отримання каталогу]: {resp_miss.text}")
        sys.exit(1)

    print("\n[Крок 3] Гарячий запит каталогу (Cache HIT / Redis Key-Value Store)...")
    start_t = time.perf_counter()
    resp_hit = session.get(f"{BASE_URL}/api/v1/items/?skip=0&limit=10")
    hot_duration_ms = (time.perf_counter() - start_t) * 1000

    cache_header_hit = resp_hit.headers.get("X-Cache", "NONE")
    inst_hit = resp_hit.headers.get("X-Instance-ID", "unknown")
    print(
        f"  HTTP {resp_hit.status_code} | Час: {hot_duration_ms:.2f} ms | X-Cache: [{cache_header_hit}] | Інстанс: [{inst_hit}]"
    )

    if cache_header_hit == "HIT":
        speedup = cold_duration_ms / max(hot_duration_ms, 0.001)
        print(
            f"  [ПІДТВЕРДЖЕНО] Кешування активне! Прискорення (Speedup): x{speedup:.1f} рази."
        )
    else:
        print(
            f"  [ЗВЕРНІТЬ УВАГУ] Очікувався X-Cache: HIT, отримано: {cache_header_hit}"
        )

    print(
        "\n[Крок 4] Серія з 5 послідовних запитів для перевірки стабільності Cache HIT:"
    )
    for i in range(1, 6):
        t0 = time.perf_counter()
        r = session.get(f"{BASE_URL}/api/v1/items/?skip=0&limit=10")
        dt = (time.perf_counter() - t0) * 1000
        print(
            f"  Запит #{i}: HTTP {r.status_code} | {dt:5.2f} ms | X-Cache: {r.headers.get('X-Cache')} | Інстанс: [{r.headers.get('X-Instance-ID')}]"
        )
        time.sleep(0.1)

    print("\n[Крок 5] Тестування інвалідації кешу (Cache Invalidation on Mutation)...")
    print("  1. Авторизація адміністратора...")
    login_resp = session.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": "netrunner_admin", "password": "AdminSecret2026!"},
    )
    if login_resp.status_code != 200:
        print(f"  [Помилка логіну]: {login_resp.status_code}")
        return

    token = login_resp.json().get("access_token")
    auth_headers = {"Authorization": f"Bearer {token}"}

    unique_slug = f"cyber-implant-test-{uuid.uuid4().hex[:6]}"
    new_item_payload = {
        "title": "Kiroshi Optics Mk.4 Test",
        "slug": unique_slug,
        "description": "Тестовий імплант для перевірки інвалідації розподіленого кешу",
        "price": 4500.0,
        "category": "CYBERWARE",
        "stock": 5,
        "is_active": True,
    }

    print(f"  2. Створення нового товару із slug='{unique_slug}'...")
    create_resp = session.post(
        f"{BASE_URL}/api/v1/items/", json=new_item_payload, headers=auth_headers
    )
    print(
        f"  HTTP {create_resp.status_code} | Інстанс створення: [{create_resp.headers.get('X-Instance-ID')}]"
    )

    print("  3. Повторне зчитування каталогу після додавання товару:")
    t0 = time.perf_counter()
    resp_after = session.get(f"{BASE_URL}/api/v1/items/?skip=0&limit=10")
    dt_after = (time.perf_counter() - t0) * 1000
    cache_header_after = resp_after.headers.get("X-Cache", "NONE")
    print(
        f"  HTTP {resp_after.status_code} | Час: {dt_after:.2f} ms | X-Cache: [{cache_header_after}]"
    )

    if cache_header_after == "MISS":
        print(
            "  [ПІДТВЕРДЖЕНО] Інвалідація спрацювала! Попередній кеш скинуто, дані оновлено з БД."
        )
    else:
        print(
            f"  [УВАГА] Статус X-Cache: {cache_header_after}. Перевірте виклик delete_cache_pattern()."
        )

    print("\n" + "=" * 75)
    print("ТЕСТУВАННЯ РОЗПОДІЛЕНОГО КЕШУВАННЯ УСПІШНО ЗАВЕРШЕНО.")
    print("=" * 75)


if __name__ == "__main__":
    run_cache_verification()
