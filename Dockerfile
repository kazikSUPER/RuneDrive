# Базовий образ: легкий та безпечний Python 3.12 на базі Debian Bookworm Slim
FROM python:3.12-slim

# Налаштування змінних середовища для оптимізації роботи Python у контейнері
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/application/src

# Встановлення робочої директорії
WORKDIR /application

# Створення безпечного користувача без root-привілеїв (DevOps Best Practice)
RUN groupadd --gid 10001 application_group && \
    useradd --uid 10001 --gid 10001 --shell /bin/bash --create-home application_user

# Спочатку копіюємо лише файл залежностей для ефективного кешування Docker-шарів
COPY requirements.txt .

# Встановлення залежностей проєкту без кешування pip (зменшує розмір фінального образу)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копіюємо вихідний код проєкту та конфігурації
COPY src/ ./src/
COPY pyproject.toml .

# Передаємо права власності непривілейованому користувачу
RUN chown -R application_user:application_group /application

# Перемикаємося на безпечного користувача
USER application_user

# Відкриваємо порт застосунку
EXPOSE 8000

# Перевірка життєздатності контейнера (Healthcheck)
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

# Команда запуску асинхронного ASGI-сервера Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
