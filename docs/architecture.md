# Архітектурна специфікація системи «RuneDrive»

## 1. Загальний опис та обґрунтування предметної області
**RuneDrive** — це високонавантажена цифрова платформа (E-commerce / Digital Distribution), що спеціалізується на торгівлі кібернетичними імплантами, цифровими магічними рунами (прошивками) та алхімічними еліксирами у всесвіті Arcanepunk.

### Чому обрана ця предметна область для Highload-курсу:
1. **Екстремальні пікові навантаження (Flash Sales):** Рідкісні артефакти (наприклад, імплант «Кіроші Mk.3» або «Еліксир нескінченної мани») викидаються обмеженим тиражем (наприклад, 100 одиниць на 50 000 користувачів). Це ідеальний полігон для вивчення Race Condition, оптимістичних та песимістичних блокувань (`SELECT ... FOR UPDATE`), атомарних операцій у Redis (`DECR`, Lua-скрипти).
2. **Гетерогенні дані (JSONB):** Різні категорії товарів мають кардинально різні специфікації (імпланти потребують параметрів слотів, напруги та нейросумісності; зілля — час дії, об'єм та температуру). Використання PostgreSQL `JSONB` демонструє переваги комбінації реляційної надійності та документного NoSQL підходу.
3. **Розподіл I/O-bound та CPU-bound навантаження:**
   - **I/O-bound:** пошук за каталогом, фільтрація за характеристиками, транзакційна фіксація замовлень.
   - **CPU-bound:** валідація цифрових підписів токенів та рун, криптографічна перевірка ліцензій на прошивки.

---

## 2. Реальна архітектура системи (Mermaid)

```mermaid
flowchart TD
    Client["Клієнти<br>(Swagger UI / Браузер / Pytest / API)"]

    subgraph AppLayer ["FastAPI Application (Python 3.12 / Uvicorn)"]
        Router["API Routers (v1)<br>• /auth, /users, /items<br>• /vendor, /admin, /health"]
        Security["Security and RBAC Layer<br>• JWT Bearer (HS256)<br>• bcrypt Password Hashing<br>• IDOR Protection"]
        Schemas["Pydantic V2 Schemas (DTO)<br>• Валідація вхідних даних<br>• Фільтрація вихідних відповідей"]
        ORM["SQLAlchemy 2.0 Async ORM<br>(Пул з'єднань asyncpg)"]
    end

    subgraph StorageLayer ["Data and Cache Infrastructure (Docker Compose)"]
        Redis[("Redis 7<br>• L2 Кешування каталогу<br>• Атомарні лічильники Flash-sales<br>• Розподілені блокування")]
        Postgres[("PostgreSQL 16<br>• Таблиці users, items<br>• JSONB характеристики імплантів<br>• ACID-транзакції")]
    end

    Client -->|"HTTP JSON / Bearer Token"| Router
    Router --> Security
    Router --> Schemas
    Router --> ORM

    ORM <-->|"Кешування та блокування"| Redis
    ORM -->|"Асинхронні SQL-запити (asyncpg)"| Postgres
```

---

## 3. Компоненти системи та їх відповідальність

| Компонент | Технологія | Роль у системі |
| :--- | :--- | :--- |
| **API Backend** | FastAPI (Python 3.12 + Uvicorn) | Асинхронна неблокуюча обробка HTTP-запитів (ASGI), маршрутизація, автоматична генерація OpenAPI / Swagger UI. |
| **Шар безпеки (Auth & RBAC)** | PyJWT + Passlib (bcrypt) | Stateless автентифікація за JWT-токенами, хешування паролів із сіллю, перевірка ролей (BUYER, RIPPERDOC, ADMIN) та захист від IDOR. |
| **Шар передачі даних (DTO)** | Pydantic V2 | Сувора типізація та валідація вхідних запитів, серіалізація та захист від витоку внутрішніх полів моделей. |
| **База даних (RDBMS)** | PostgreSQL 16 + asyncpg | Надійне транзакційне збереження даних користувачів та товарів, підтримка JSONB-специфікацій для гнучких характеристик артефактів. |
| **In-Memory сховище** | Redis 7 | L2-кешування вибірок каталогу для розвантаження бази, атомарні операції та розподілені блокування. |
| **Контроль якості та тести** | Pytest, Ruff, Pre-commit | Наскрізне асинхронне тестування бізнес-логіки та матриці доступу, лінтинг та форматування коду. |

---

## 4. Потенціал еволюції до мікросервісної архітектури (DevOps & Cloud Native)

Поточна кодова база спроєктована за принципом **модульного моноліту (Modular Monolith)** з чітким розділенням бізнес-доменів (Domain-Driven Design). Це створює прямий потенціал для швидкої декомпозиції системи на мікросервіси в межах дисципліни **«DevOps інфраструктура та хмарні технології» (викладач Дячук Р.Л.)**.

### 4.1. Чому RuneDrive легко декомпозується
1. **Stateless автентифікація (JWT HS256):** Токени містять усю необхідну інформацію (`sub: UUID`, `role: UserRole`, `exp`). Будь-який незалежний мікросервіс валідує криптографічний підпис токена локально за спільним `SECRET_KEY` без звернення до бази користувачів.
2. **Ізоляція доменів даних:** Сутності бази даних чітко розмежовані на користувачів (`users`), каталог товарів (`items`) та замовлення (`orders`).

### 4.2. Цільова мікросервісна архітектура (Mermaid)

```mermaid
flowchart TD
    Client["Клієнти (Web / Mobile / API)"]

    subgraph IngressLayer ["Ingress and Routing Layer (Kubernetes / Traefik)"]
        Gateway["API Gateway / K8s Ingress Controller<br>• SSL Termination<br>• Маршрутизація за шляхами"]
    end

    subgraph MicroservicesCluster ["Автономні мікросервіси"]
        AuthService["Auth and Identity Service (FastAPI)<br>• Порт: 8001<br>• Логін, реєстрація, випуск JWT"]
        CatalogService["Catalog and Inventory Service (FastAPI)<br>• Порт: 8002<br>• Перегляд та керування імплантами"]
        OrderService["Order and Payment Service (FastAPI)<br>• Порт: 8003<br>• Транзакції та захист від Race Condition"]
    end

    subgraph DatabasePerService ["Ізольовані сховища даних (Database per Service)"]
        AuthDB[("PostgreSQL: users_db<br>• Акаунти та хеші bcrypt")]
        CatalogDB[("PostgreSQL: catalog_db<br>• Каталог та JSONB характеристики")]
        OrderDB[("PostgreSQL: orders_db<br>• Замовлення та чеки")]
        SharedRedis[("Redis Cluster<br>• L2 кешування каталогу<br>• Розподілені блокування замовлень")]
    end

    Client --> Gateway

    Gateway -->|"/api/v1/auth/*, /users/*"| AuthService
    Gateway -->|"/api/v1/items/*, /vendor/*"| CatalogService
    Gateway -->|"/api/v1/orders/*"| OrderService

    AuthService --> AuthDB
    CatalogService --> CatalogDB
    CatalogService <--> SharedRedis
    OrderService --> OrderDB
    OrderService <--> SharedRedis
```

### 4.3. Практична цінність для DevOps
* **Контейнеризація та Kubernetes (k8s):** Окремі маніфести `Deployment` та `Service` для кожного мікросервісу. Можливість налаштування `HorizontalPodAutoscaler (HPA)` окремо для Catalog Service (який отримує 90% трафіку читання) без надлишкового масштабування сервісу авторизації.
* **CI/CD пайплайни (GitHub Actions):** Налаштування незалежних матричних збірок (`matrix builds`) і умовного тестування: зміни в каталозі викликають збірку тільки Docker-образу `runedrive-catalog`.
* **Розподілений моніторинг (Prometheus / Grafana):** Збір персональних метрик (RPS, Latency p95/p99, Error Rate) з кожного мікросервісу через єдиний Ingress.
* **Інфраструктура як код (IaC / Terraform):** Опис хмарних ресурсів, мереж і сховищ окремо під кожен сервіс.
