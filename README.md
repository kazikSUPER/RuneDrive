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
│   ├── test_stateless.py    # Тест консистентності безстанової архітектури (Лаб 2)
│   └── test_balancing.py    # Демонстрація балансування та failover (Лаб 3)
└── src/
    └── app/
        ├── main.py          # ASGI точка входу, X-Instance-ID Middleware, Lifespan
        ├── core/            # Конфігурація (Pydantic Settings), DB підключення, безпека
        ├── models/          # Моделі SQLAlchemy (User, Item, Order, OrderItem)
        ├── schemas/         # Pydantic DTO схеми валідації та серіалізації
        └── api/v1/          # REST API ендпоінти (/auth, /users, /items, /orders, /health)
```

---

## 4. Запуск кластера та тестування

### 4.1. Запуск повного кластера (Docker Compose)
```bash
docker compose up --build -d
```
Склад запущених сервісів:
- **Nginx (Load Balancer):** [http://localhost:8080](http://localhost:8080)
- **Interactive Swagger Docs (через балансувальник):** [http://localhost:8080/docs](http://localhost:8080/docs)
- **Health Check Endpoint:** [http://localhost:8080/api/v1/health](http://localhost:8080/api/v1/health)

### 4.2. Перевірка Лабораторної №2 (Stateless Test)
```bash
python scripts/test_stateless.py
```
*Скрипт авторизується, отримує JWT токен і робить запити до різних реплік, демонструючи, що авторизація та операції замовлення виконуються однаково незалежно від репліки, яка обробляє запит.*

### 4.3. Перевірка Лабораторної №3 (Load Balancing & Failover Test)
```bash
python scripts/test_balancing.py
```
*Скрипт надсилає серію з 20 запитів і виводить статистику розподілу між `runedrive-api-1` та `runedrive-api-2`.*

**Перевірка відмовостійкості (Failover):**
1. В окремому терміналі вимкніть перший інстанс:
   ```bash
   docker stop runedrive_api_1
   ```
2. Повторно запустіть:
   ```bash
   python scripts/test_balancing.py
   ```
3. Nginx автоматично спрямує 100% запитів на `runedrive-api-2`, не повернувши жодної помилки 502/503.
4. Повернення інстансу в кластер:
   ```bash
   docker start runedrive_api_1
   ```
