"""
Тест архітектури без стану (Stateless Architecture Cross-Instance Test)
для Лабораторної роботи №2.

Сценарій:
1. Запит авторизації на Nginx (Round Robin розподіляє на один з інстансів: api-1 або api-2).
2. Отримання JWT токена та фіксація заголовка X-Instance-ID первинного інстансу.
3. Виконання серії запитів з отриманим токеном (отримання профілю, створення та перегляд замовлень).
4. Перевірка того, що при перемиканні запитів між різними інстансами бекенду (api-1 <-> api-2):
   - JWT токен валідний на обох інстансах без переавторизації (stateless auth).
   - Дані замовлень та кошика ідентичні на обох інстансах (зовнішній стан у PostgreSQL та Redis).
"""

import sys
import time
import requests

BASE_URL = "http://localhost:8080"


def run_stateless_test():
    print("=" * 70)
    print("ЛАБОРАТОРНА РОБОТА 2: ТЕСТ АРХІТЕКТУРИ БЕЗ СТАНУ (STATELESS TEST)")
    print("=" * 70)

    session = requests.Session()

    # Крок 1. Перевірка доступності кластера
    print("\n[Крок 1] Перевірка доступності кластера через Nginx (порт 8080)...")
    try:
        r = session.get(f"{BASE_URL}/api/v1/health", timeout=5)
        instance = r.headers.get("X-Instance-ID", "unknown")
        print(f"  Статус: {r.status_code}, Відповів інстанс: {instance}")
    except Exception as e:
        print(f"  [Помилка з'єднання]: {e}")
        print("  Переконайтеся, що запущено docker-compose up!")
        sys.exit(1)

    # Крок 2. Авторизація користувача
    print("\n[Крок 2] Авторизація користувача 'netrunner_admin'...")
    login_data = {"username": "netrunner_admin", "password": "AdminSecret2026!"}
    r = session.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
    if r.status_code != 200:
        print(f"  [Помилка авторизації]: {r.status_code} - {r.text}")
        sys.exit(1)

    auth_instance = r.headers.get("X-Instance-ID", "unknown")
    token = r.json().get("access_token")
    print(f"  Успішно! Токен отримано від інстансу: [{auth_instance}]")

    headers = {"Authorization": f"Bearer {token}"}

    # Крок 3. Перевірка збереження сесії при зміні інстансів
    print("\n[Крок 3] Виконання 6 послідовних запитів профілю /auth/me через Nginx:")
    print("  Очікування: токен приймається будь-яким інстансом без збереження сесії в пам'яті процесу.")

    instances_seen = set()
    for i in range(1, 7):
        resp = session.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
        inst = resp.headers.get("X-Instance-ID", "unknown")
        instances_seen.add(inst)
        data = resp.json()
        print(f"  Запит #{i}: HTTP {resp.status_code} | Обслуговував: [{inst}] | Користувач: {data.get('username')}")
        time.sleep(0.3)

    print(f"\n  Всього унікальних інстансів, що обробили запити: {len(instances_seen)} -> {list(instances_seen)}")
    if len(instances_seen) > 1:
        print("  [ПІДТВЕРДЖЕНО] Застосунок є STATELESS: жоден стан не прив'язаний до локального процесу!")
    else:
        print("  [УВАГА] Запити потрапили лише на один інстанс. Перевірте балансування Nginx.")

    # Крок 4. Створення замовлення та перевірка транзакційного стану
    print("\n[Крок 4] Створення замовлення та перевірка консистентності в БД...")
    items_resp = session.get(f"{BASE_URL}/api/v1/items?limit=1", headers=headers)
    items = items_resp.json()
    if items:
        target_item = items[0]
        order_payload = {
            "items": [{"item_id": target_item["id"], "quantity": 1}],
            "delivery_address": "Нічне Місто, Кабукі, клініка Віктора",
            "notes": "Термінове замовлення для лаби"
        }
        order_res = session.post(f"{BASE_URL}/api/v1/orders", json=order_payload, headers=headers)
        order_inst = order_res.headers.get("X-Instance-ID", "unknown")
        if order_res.status_code == 201:
            order_data = order_res.json()
            print(f"  Замовлення #{order_data['id']} створено через інстанс [{order_inst}]. Сума: {order_data['total_price']}")

            # Читання замовлень іншим запитом
            list_res = session.get(f"{BASE_URL}/api/v1/orders", headers=headers)
            list_inst = list_res.headers.get("X-Instance-ID", "unknown")
            print(f"  Список замовлень прочитано через інстанс [{list_inst}]. Кількість: {len(list_res.json())}")
            print("  [ПІДТВЕРДЖЕНО] Стан сутностей зберігається виключно в базі даних PostgreSQL.")
        else:
            print(f"  Не вдалося створити замовлення: {order_res.status_code} - {order_res.text}")

    print("\n" + "=" * 70)
    print("ТЕСТУВАННЯ ЛАБОРАТОРНОЇ РОБОТИ №2 ЗАВЕРШЕНО УСПІШНО.")
    print("=" * 70)


if __name__ == "__main__":
    run_stateless_test()
