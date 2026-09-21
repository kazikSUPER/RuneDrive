# RuneDrive: Highload Marketplace API

> Навчальний проєкт з дисципліни **«Розробка високонавантажених систем на Python»** (4 курс, 1 семестр, ІФТКН ЧНУ).
> **Викладач:** доц. Красовський С.В.
> **Студент:** Казімір В.І. (група 443Б)

---

## Стек технологій
- **Мова:** Python 3.12+
- **Фреймворк:** FastAPI (ASGI)
- **База даних:** PostgreSQL 16 (драйвер `asyncpg`, ORM `SQLAlchemy 2.0 Async`)
- **Контроль якості:** `Ruff` (linter + formatter)
- **Автоматизація:** `pre-commit` Git-хуки

---

## Структура репозиторію
```
.
├── .gitignore              # Ігнорування venv, кешу та конфіденційних файлів
├── .pre-commit-config.yaml # Конфігурація Git-хуків якості коду
├── pyproject.toml          # Метадані проєкту та налаштування лінтера Ruff
├── requirements.txt        # Перелік залежностей
├── docs/
│   └── architecture.md     # Архітектурна схема системи та опис компонентів
└── src/
    └── app/
        ├── main.py         # Точка входу FastAPI сервера
        ├── core/
        │   ├── config.py   # Pydantic-конфігурація середовища
        │   └── database.py # Асинхронне підключення до PostgreSQL
        ├── models/         # Моделі SQLAlchemy (Item, Base)
        ├── schemas/        # Pydantic V2 валідаційні схеми
        └── api/v1/         # Версіоновані REST API ендпоінти
```

---

## Встановлення та запуск

### 1. Клонування та перехід
```bash
cd "D:\ІФТКН\4 КУРС\1 семестр\Розробка високонавантажених систем на Python\+"
```

### 2. Створення та активація оточення
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Встановлення залежностей
```powershell
pip install -r requirements.txt
```

### 4. Налаштування Pre-commit хуків
```powershell
pre-commit install
pre-commit run --all-files
```

### 5. Запуск сервера розробки
```powershell
uvicorn src.app.main:app --reload --port 8000
```
- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Redoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health check:** [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)
