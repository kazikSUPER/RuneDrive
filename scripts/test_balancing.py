import subprocess
import time
from collections import Counter

import requests

BASE_URL = "http://localhost:8080"
TOTAL_REQUESTS = 100


def get_container_name_map() -> dict:
    """Отримує словник відповідності: {12_char_hostname: container_name} напряму з Docker CLI."""
    mapping = {}
    try:
        cmd = ["docker", "ps", "--format", "{{.ID}}|{{.Names}}"]
        output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
        for line in output.splitlines():
            if "|" in line:
                cid, cname = line.strip().split("|", 1)
                mapping[cid.strip()] = cname.strip()
    except Exception:
        pass
    return mapping


def run_balancing_test():
    print("=" * 70)
    print("ТЕСТ БАЛАНСУВАННЯ ТА ГОРИЗОНТАЛЬНОГО МАСШТАБУВАННЯ КЛАСТЕРА")
    print("=" * 70)

    session = requests.Session()
    counter = Counter()
    status_counter = Counter()

    container_map = get_container_name_map()

    print(
        f"\n[Крок 1] Відправка {TOTAL_REQUESTS} послідовних запитів через балансувальник Nginx..."
    )

    for i in range(1, TOTAL_REQUESTS + 1):
        try:
            start_t = time.time()
            resp = session.get(f"{BASE_URL}/api/v1/health", timeout=3)
            elapsed_ms = (time.time() - start_t) * 1000

            raw_inst = resp.headers.get("X-Instance-ID", "unknown")
            friendly_name = container_map.get(raw_inst, raw_inst)

            counter[friendly_name] += 1
            status_counter[resp.status_code] += 1

            print(
                f"  Запит #{i:02d}: Статус HTTP {resp.status_code} | "
                f"Час: {elapsed_ms:5.1f} ms | Інстанс: [{friendly_name}]"
            )
            time.sleep(0.1)
        except Exception as e:
            print(f"  Запит #{i:02d}: Помилка з'єднання: {e}")
            status_counter["FAILED"] += 1

    print("\n" + "-" * 50)
    print("РЕЗУЛЬТАТИ РОЗПОДІЛУ НАВАНТАЖЕННЯ (STATISTICS):")
    print("-" * 50)
    for inst, count in sorted(counter.items()):
        pct = (count / TOTAL_REQUESTS) * 100
        print(f"  Інстанс [{inst}]: {count} запитів ({pct:.1f}%)")

    print(f"\nСтатуси відповідей: {dict(status_counter)}")

    if len(counter) > 1:
        print(
            "\n[ПІДТВЕРДЖЕНО] Балансування працює! Усі масштабовані інстанси беруть участь у навантаженні."
        )
    elif len(counter) == 1:
        print("\n[ЗВЕРНІТЬ УВАГУ] Весь трафік пішов на один інстанс.")


if __name__ == "__main__":
    run_balancing_test()
