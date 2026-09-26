"""
Тест горизонтального масштабування та балансування навантаження (Load Balancing Test)
для Лабораторної роботи №3.

Сценарій:
1. Відправка серії HTTP запитів (20 запитів) через Nginx Load Balancer (http://localhost:8080/api/v1/health).
2. Фіксація розподілу навантаження між бекендами: api-1 та api-2 на основі заголовка X-Instance-ID.
3. Розрахунок статистики та демонстрація алгоритму (Round Robin / Least Connections / IP Hash).
4. Перевірка механізму відмовостійкості (Failover & Resilience):
   Якщо один інстанс вимкнути (docker stop runedrive_api_1),
   Nginx непомітно перенаправляє 100% запитів на другий інстанс без 502/503 помилок.
"""

import sys
import time
from collections import Counter
import requests

BASE_URL = "http://localhost:8080"
TOTAL_REQUESTS = 20


def run_balancing_test():
    print("=" * 70)
    print("ЛАБОРАТОРНА РОБОТА 3: ТЕСТ БАЛАНСУВАННЯ ТА ГОРИЗОНТАЛЬНОГО МАСШТАБУВАННЯ")
    print("=" * 70)

    session = requests.Session()
    counter = Counter()
    status_counter = Counter()

    print(f"\n[Крок 1] Відправка {TOTAL_REQUESTS} послідовних запитів через балансувальник Nginx...")

    for i in range(1, TOTAL_REQUESTS + 1):
        try:
            start_t = time.time()
            resp = session.get(f"{BASE_URL}/api/v1/health", timeout=3)
            elapsed_ms = (time.time() - start_t) * 1000
            inst = resp.headers.get("X-Instance-ID", "unknown")
            counter[inst] += 1
            status_counter[resp.status_code] += 1

            print(f"  Запит #{i:02d}: Статус HTTP {resp.status_code} | "
                  f"Час: {elapsed_ms:5.1f} ms | Інстанс: [{inst}]")
            time.sleep(0.1)
        except Exception as e:
            print(f"  Запит #{i:02d}: Помилка з'єднання: {e}")
            status_counter["FAILED"] += 1

    print("\n" + "-" * 50)
    print("РЕЗУЛЬТАТИ РОЗПОДІЛУ НАВАНТАЖЕННЯ (STATISTICS):")
    print("-" * 50)
    for inst, count in counter.items():
        pct = (count / TOTAL_REQUESTS) * 100
        print(f"  Інстанс [{inst}]: {count} запитів ({pct:.1f}%)")

    print(f"\nСтатуси відповідей: {dict(status_counter)}")

    if len(counter) > 1:
        print("\n[ПІДТВЕРДЖЕНО] Балансування працює! Обидва інстанси беруть участь у навантаженні.")
    elif len(counter) == 1:
        print("\n[ЗВЕРНІТЬ УВАГУ] Весь трафік пішов на один інстанс.")
        print("  Якщо увімкнено IP Hash, це очікувана поведінка для одного клієнта.")
        print("  Якщо це Round Robin, перевірте працездатність обох контейнерів у docker-compose.")

    print("\n" + "=" * 70)
    print("МЕТОДИКА ПЕРЕВІРКИ ВІДМОВОСТІЙКОСТІ (FAILOVER DEMO ДЛЯ ВИКЛАДАЧА):")
    print("  1. Відкрийте інший термінал і виконайте зупинку одного контейнера:")
    print("     docker stop runedrive_api_1")
    print("  2. Запустіть цей скрипт повторно.")
    print("  3. Результат: 100% запитів успішно (HTTP 200) обслуговує [runedrive-api-2],")
    print("     клієнт не отримує ЖОДНОЇ помилки 502/503 завдяки директиві proxy_next_upstream.")
    print("  4. Поверніть інстанс назад: docker start runedrive_api_1")
    print("=" * 70)


if __name__ == "__main__":
    run_balancing_test()
