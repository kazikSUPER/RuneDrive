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

---

## 5. Розгортання в Kubernetes (Лабораторна робота №3 DevOps)

Каталог `k8s/` містить маніфести Kubernetes для розгортання повного кластера RuneDrive
у локальному minikube. Префікси імен файлів (00-…-30-) гарантують порядок застосування:
спочатку namespace, конфігурація та PVC, потім сервіси даних і наприкінці API з Ingress.

### 5.1. Склад об'єктів (`k8s/`)

| Файл | Об'єкт | Призначення |
| :--- | :--- | :--- |
| `00-namespace.yaml` | Namespace `runedrive` | Ізоляція об'єктів проєкту |
| `01-configmap.yaml` | ConfigMap | `PROJECT_NAME`, `DEBUG`, `ENVIRONMENT`, `POSTGRES_SERVER/PORT/DB/USER`, `REDIS_HOST/PORT` |
| `02-secret.yaml` | Secret | `POSTGRES_PASSWORD`, `JWT_SECRET_KEY` (демо-значення) |
| `03-postgres-pvc.yaml` | PersistentVolumeClaim | 2Gi, StorageClass `standard` |
| `10-postgres-deployment.yaml` | Deployment | PostgreSQL 16-alpine + PVC, strategy Recreate |
| `11-postgres-service.yaml` | Service | ClusterIP :5432 |
| `12-redis-deployment.yaml` | Deployment | Redis 7-alpine (кеш без персистентності) |
| `13-redis-service.yaml` | Service | ClusterIP :6379 |
| `20-api-deployment.yaml` | Deployment | 2 репліки, liveness `/api/v1/health`, readiness `/api/v1/ready`, requests/limits, RollingUpdate (maxUnavailable: 0, maxSurge: 1) |
| `21-api-service.yaml` | Service | ClusterIP :80 -> :8000 |
| `30-ingress.yaml` | Ingress | Host `runedrive.local` -> Service `runedrive-api` |

### 5.2. Підготовка середовища

```bash
minikube start --driver=docker --cpus=4 --memory=4096mb
minikube addons enable metrics-server
minikube addons enable ingress
minikube image load runedrive:1.0.0 runedrive:1.1.0
```

### 5.3. Розгортання однією командою

```bash
kubectl apply -f k8s/
kubectl rollout status deployment/runedrive-api -n runedrive
kubectl get pods,svc,pvc,ingress -n runedrive
```

### 5.4. Доступ до застосунку

```bash
kubectl port-forward svc/runedrive-api 8080:80 -n runedrive
curl http://localhost:8080/api/v1/health
curl http://localhost:8080/api/v1/ready
```

> На Windows з драйвером docker IP кластера (`minikube ip`) з хоста недосяжний без
> `minikube tunnel` (адмін-права), тому балансування та доступність демонструються
> запитами з одноразового curl-пода всередині кластера.

### 5.5. Демонстрація життєвого циклу

```bash
kubectl delete pod <POD> -n runedrive                                      # самовідновлення
kubectl scale deployment/runedrive-api --replicas=4 -n runedrive           # масштабування
```

Розподіл трафіку між репліками (різні `instance_id` у відповідях):

```bash
kubectl run curl-dist --rm -i --image=curlimages/curl --restart=Never -n runedrive -- \
  sh -c 'for i in $(seq 1 12); do curl -s http://runedrive-api/api/v1/health | grep -o "\"instance_id\":\"[^\"]*\""; done'
```

Rolling update з контролем доступності (спостерігач всередині кластера):

```bash
kubectl run av-loop --image=curlimages/curl --restart=Never -n runedrive -- \
  sh -c 'i=0; while [ $i -lt 200 ]; do curl -s -o /dev/null -w "%{http_code}\n" http://runedrive-api/api/v1/health; i=$((i+1)); sleep 0.4; done'

kubectl set image deployment/runedrive-api api=runedrive:1.1.0 -n runedrive   # rolling update
kubectl rollout status deployment/runedrive-api -n runedrive
kubectl logs av-loop -n runedrive | sort | uniq -c                            # суцільні 200
kubectl delete pod av-loop -n runedrive
kubectl rollout history deployment/runedrive-api -n runedrive              # історія
kubectl rollout undo deployment/runedrive-api -n runedrive                 # відкат
```

---

## 6. Helm-чарт (Лабораторна робота №4 DevOps)

Маніфести з ЛР№3 переписані у власний Helm-чарт `helm/runedrive/`. Усі значення
параметризовані через `values.yaml`; імена об'єктів будуються з імені релізу
(`runedrive.fullname` = `<release>-<chart>`), тож чарт можна встановлювати двічі
в один кластер без конфліктів.

### 6.1. Структура чарта

```
helm/runedrive/
├── Chart.yaml            # version: 0.1.0 (чарт), appVersion: "1.0.0" (застосунок)
├── values.yaml           # дефолти = середовище розробки (dev)
├── values-dev.yaml       # профіль dev: 2 репліки, DEBUG=true, Ingress вимкнений
├── values-prod.yaml      # профіль prod: 3 репліки, тег 1.1.0, вищі ресурси, Ingress on
└── templates/
    ├── _helpers.tpl      # runedrive.fullname + runedrive.labels (include в усіх шаблонах)
    ├── configmap.yaml    # з .Values.config; хости postgres/redis виводяться з імені релізу
    ├── secret.yaml       # значення з .Values.secrets
    ├── postgres-pvc.yaml / postgres-deployment.yaml / postgres-service.yaml
    ├── redis-deployment.yaml / redis-service.yaml
    ├── deployment.yaml / service.yaml
    ├── ingress.yaml      # генерується лише якщо .Values.ingress.enabled
    ├── pre-upgrade-hook.yaml   # хук pre-upgrade: перевірка здоров'я релізу
    ├── tests/test-connection.yaml  # тест релізу (helm test)
    └── NOTES.txt
```

### 6.2. version vs appVersion у Chart.yaml

- `version: 0.1.0` — версія **самого чарта** як пакета шаблонів і значень. Змінюється,
  коли змінюються шаблони чи дефолти чарта; використовується Helm для відстеження
  релізів чарта та при публікації в реєстр.
- `appVersion: "1.0.0"` — версія **застосунку**, який чарт розгортає. Для RuneDrive це
  базова версія API (інформаційна; фактичний тег образу задається `image.tag` у values).

### 6.3. Таблиця параметрів values.yaml

| Параметр | Дефолт (dev) | values-prod | Опис |
| :--- | :--- | :--- | :--- |
| `image.repository` / `image.tag` | `runedrive` / `1.0.0` | `runedrive` / `1.1.0` | Репозиторій і тег образу API |
| `image.pullPolicy` | `IfNotPresent` | те саме | Політика завантаження образу |
| `replicaCount` | `2` | `3` | Кількість реплік API |
| `service.type` / `service.port` | `ClusterIP` / `80` | те саме | Тип і порт сервісу |
| `resources.requests` / `resources.limits` | 100m/256Mi, 500m/512Mi | 250m/512Mi, 1/1Gi | Ресурси API |
| `config.ENVIRONMENT` / `config.APP_ENV` | `k8s-dev` | `k8s-production` | Ім'я середовища |
| `config.PROJECT_NAME` | `RuneDrive API` | те саме | Назва проєкту |
| `config.DEBUG` | `true` | `false` | Режим налагодження |
| `config.POSTGRES_PORT/DB/USER` | 5432 / runedrive / runedrive | те саме | Параметри БД |
| `config.REDIS_PORT` | `6379` | те саме | Порт кешу |
| `ingress.enabled` / `ingress.host` | `false` / `runedrive.local` | `true` / `runedrive.local` | Увімкнення Ingress |
| `postgres.image` | `postgres:16-alpine` | те саме | Образ БД |
| `postgres.persistence.enabled/size/storageClass` | `true` / `2Gi` / `standard` | те саме | PVC для БД |
| `postgres.resources` | 100m/256Mi, 500m/512Mi | те саме | Ресурси БД |
| `redis.image` / `redis.resources` | `redis:7-alpine` / мінімальні | те саме | Кеш |
| `secrets.POSTGRES_PASSWORD` / `secrets.JWT_SECRET_KEY` | демо-значення | демо-значення | → Secret (реальні паролі не зберігаються) |

> `POSTGRES_SERVER` і `REDIS_HOST` у ConfigMap не задаються у values — вони виводяться
> з імені релізу шаблоном (`<release>-postgres`, `<release>-redis`).

### 6.4. Перевірка та порівняння середовищ (без встановлення)

```bash
helm lint helm/runedrive
helm template runedrive helm/runedrive                       # дефолти (dev)
helm template runedrive helm/runedrive -f helm/runedrive/values-prod.yaml
```

### 6.3. Встановлення (на чистий namespace)

```bash
kubectl delete namespace runedrive   # прибрати реліз ЛР№3
helm install runedrive helm/runedrive -n runedrive --create-namespace
helm list -n runedrive
helm get values runedrive -n runedrive
```

### 6.4. Життєвий цикл релізу

```bash
helm upgrade runedrive helm/runedrive --set image.tag=1.1.0 -n runedrive   # rev 2 (--set)
helm upgrade runedrive helm/runedrive -f helm/runedrive/values-prod.yaml -n runedrive  # rev 3 (prod)
helm test runedrive -n runedrive                                           # тест релізу
helm history runedrive -n runedrive                                        # ревізії 1-4
helm rollback runedrive 1 -n runedrive                                     # rev 4 = копія rev 1
helm uninstall runedrive -n runedrive                                      # чистка всього
```

Стан релізів Helm зберігає у Secret'ах namespace:
`sh.helm.release.v1.runedrive.v<N>` з міткою `owner=helm`.
