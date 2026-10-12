# RuneDrive: Високонавантажений кластер маркетплейсу

---

## 1. Стек технологій
- **Мова програмування:** Python 3.12
- **Асинхронний веб-фреймворк:** FastAPI (ASGI, Uvicorn)
- **Балансувальник навантаження / Reverse Proxy:** Nginx 1.25 Alpine
- **База даних:** PostgreSQL 16 (`asyncpg`, `SQLAlchemy 2.0 Async`)
- **Швидке кешування та блокування:** Redis 7 Alpine
- **Контроль якості:** `Ruff` (linter + formatter), `pre-commit` Git-хуки

---

## 2. Реалізовані лабораторні роботи

### Лабораторна робота №1: «Проєктування архітектури та базовий прототип системи»
- Спроєктовано модульну архітектуру (Modular Monolith) платформи **RuneDrive** для торгівлі кібернетичними імплантами та рунами.
- Реалізовано 3 ключові доменні сутності з повноцінними зв'язками: `User` (покупці, ріппердоки, адміни), `Item` (товари з гнучкими JSONB характеристиками), `Order` / `OrderItem` (замовлення з транзакційним списанням зі складу).
- Підготовлено архітектурну специфікацію, C4 діаграму контейнерів та аналіз вузьких місць (Bottleneck Analysis) у [docs/architecture.md](docs/architecture.md).

### Лабораторна робота №2: «Архітектура без стану (Stateless Application Architecture)»
- Проведено аудит стану системи: стан сесій переведено на безстанові JWT токени (HS256), персистентний стан винесено у спільну PostgreSQL, кеш — у Redis.
- Реалізовано HTTP Middleware для відстеження обробника запиту з прокиданням заголовка `X-Instance-ID`.
- Розгорнуто дві незалежні репліки бекенду (`api-1` та `api-2`) у спільному Docker-оточенні.
- Створено автоматизований тест перевірки консистентності сесій між репліками: `scripts/test_stateless.py`.

### Лабораторна робота №3: «Горизонтальне масштабування та балансування навантаження»
- Розгорнуто Nginx як Reverse Proxy / Load Balancer перед пулом реплік `api-1` та `api-2`.
- Налаштовано алгоритми балансування трафіку: `Round Robin` (активний за замовчуванням), `Least Connections` (`least_conn`) та `IP Hash` (`ip_hash`).
- Налаштовано механізм відмовостійкості (Failover) через директиву `proxy_next_upstream`: при падінні одного з бекендів Nginx прозоро перенаправляє трафік на живий інстанс без 5xx помилок для клієнта.
- Створено демонстраційний скрипт розподілу запитів та відмовостійкості: `scripts/test_balancing.py`.

### Лабораторна робота №4: «Розподілене кешування (Distributed Caching) та паттерни узгодженості даних»
- Інтегровано централізований кешувальний шар **Redis 7** у якості distributed L2 cache для read-intensive ендпоінтів.
- Реалізовано патерн **Cache-Aside (Lazy Loading)** для `GET /api/v1/items` та `GET /api/v1/items/{id}`.
- Впроваджено схему ієрархічних ключів: `items:catalog:skip_{skip}:limit_{limit}` (TTL=120s), `items:detail:{item_id}` (TTL=300s).
- Реалізовано **примусову інвалідацію** кешу при мутуючих операціях (`POST`, `PATCH`, `DELETE`) через `delete_cache_pattern("items:catalog:*")` та `delete_cache("items:detail:{id}")`.
- Додано HTTP-заголовок `X-Cache: HIT/MISS` у кожну відповідь для детермінованої діагностики джерела даних.
- Виміряна різниця затримок: Cache MISS (PostgreSQL) ~24.7 мс vs Cache HIT (Redis) ~1.8 мс → **прискорення у 13.4 рази**.
- Реалізовано **Graceful Fallback**: при відмові Redis всі запити безпомилково продовжують обслуговуватись через PostgreSQL (модуль `src/app/core/redis.py`).
- Автоматизований демонстраційний скрипт: `scripts/test_distributed_cache.py`.

### Лабораторна робота №5: «Навантажувальне тестування (Load & Performance Baseline)»
- Розроблено 3 бізнес-сценарії навантаження у `locustfile.py`: Scenario A (Read-Intensive), Scenario B (Auth/Write CPU), Scenario C (Full Profile Workflow).
- Виміряно **System Performance Baseline**: 100 VUs → **280.4 RPS**, p50=17ms, p95=94ms, Error Rate=**0.0%**.
- Визначено **Saturation Point** (~160-180 VUs / ~320 RPS): при 1000 VUs Throughput лише 398.8 RPS, p50=1400ms, помилок 99%.
- **Виявлені Bottlenecks:** bcrypt CPU-bound hashing (Scenario B) + Nginx 5s upstream queue timeout.
- Проведено порівняльний аналіз: 1 vs 5 інстансів (Scalability Efficiency=85.8%), Cold DB vs Warm Redis (80%+ розвантаження БД).
- Усі CSV-звіти прогонів збережено у директорії `benchmarks/`.

---

## 3. Структура проєкту

```
.
├── docker-compose.yml       # Оркестрація: Nginx (8080), api-1, api-2, PostgreSQL, Redis
├── Dockerfile               # Контейнеризація FastAPI застосунку
├── pyproject.toml           # Налаштування Ruff
├── requirements.txt         # Python залежності
├── nginx/
│   └── nginx.conf           # Конфігурація Upstream пулу, алгоритмів та Failover
├── docs/
│   └── architecture.md      # C4 діаграма, State Audit, Bottleneck Analysis
├── scripts/
│   ├── test_stateless.py         # Тест консистентності безстанової архітектури (Лаб 2)
│   ├── test_balancing.py         # Демонстрація балансування та failover (Лаб 3)
│   └── test_distributed_cache.py # Верифікація кешування: HIT/MISS/Invalidation (Лаб 4)
└── src/
    └── app/
        ├── main.py          # ASGI точка входу, X-Instance-ID Middleware, Lifespan
        ├── core/
        │   ├── config.py    # Pydantic Settings, env-файл стратегія
        │   ├── database.py  # Async SQLAlchemy engine та session pool
        │   ├── redis.py     # Redis кешування: get/set/delete, Graceful Fallback (Лаб 4)
        │   └── security.py  # JWT (bcrypt hashing, token encode/decode)
        ├── models/          # Моделі SQLAlchemy (User, Item, Order, OrderItem)
        ├── schemas/         # Pydantic DTO схеми валідації та серіалізації
        └── api/v1/          # REST API ендпоінти (/auth, /users, /items, /orders, /health)
```

---

## 4. Запуск кластера та тестування

### 4.1. Запуск повного кластера (5 інстансів)
```bash
docker compose up --scale api=5 -d
```
Склад запущених сервісів:
- **Nginx (Load Balancer):** [http://localhost:8080](http://localhost:8080)
- **Interactive Swagger Docs:** [http://localhost:8080/docs](http://localhost:8080/docs)
- **Health Check:** [http://localhost:8080/api/v1/health](http://localhost:8080/api/v1/health)

### 4.2. Перевірка Лаб №2 (Stateless Test)
```bash
python scripts/test_stateless.py
```

### 4.3. Перевірка Лаб №3 (Load Balancing & Failover)
```bash
python scripts/test_balancing.py
```

### 4.4. Перевірка Лаб №4 (Distributed Cache: HIT/MISS/Invalidation/Fallback)
```bash
python scripts/test_distributed_cache.py
```
Скрипт демонструє:
1. Перший запит — `X-Cache: MISS`, зчитування з PostgreSQL (~25 мс).
2. Повторний запит — `X-Cache: HIT`, відповідь з Redis (~1.8 мс), прискорення x13+.
3. Після `POST /items` — наступне читання знову `X-Cache: MISS` (інвалідація спрацювала).
4. Зупиніть Redis (`docker stop redis`) — запити продовжують відповідати HTTP 200 (Graceful Fallback).

### 4.5. Перевірка Лаб №5 (Load & Performance Baseline — Locust)
```bash
# Інтерактивний Web UI на http://localhost:8089
locust -f locustfile.py --host=http://localhost:8080

# Автоматизований headless-прогін (100 VUs, 60 секунд)
locust -f locustfile.py --host=http://localhost:8080 --headless -u 100 -r 5 --run-time 60s --csv=benchmarks/run_baseline
```

**Зафіксований Performance Baseline:**
| VUs | RPS | p50 | p95 | Errors |
|-----|-----|-----|-----|--------|
| 10  | 64.8 | 6 ms | 18 ms | 0% |
| 50  | 184.2 | 9 ms | 42 ms | 0% |
| **100** | **280.4** | **17 ms** | **94 ms** | **0.0%** |
| 200 | 312.6 | 55 ms | 480 ms | 1.2% |
| 1000 | 398.8 | 1400 ms | 6400 ms | 99% |
