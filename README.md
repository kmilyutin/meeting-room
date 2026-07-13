# Booked!

Сервис поиска и бронирования переговорных комнат.

## Запуск через Docker

Требования: Git и Docker Compose.

```bash
git clone https://github.com/kmilyutin/meeting-room.git
cd meeting-room
cp .env.example .env
docker compose -f docker/docker-compose.yml up --build -d
docker compose -f docker/docker-compose.yml exec web python manage.py migrate
docker compose -f docker/docker-compose.yml exec web python manage.py loaddata equipment rooms
docker compose -f docker/docker-compose.yml exec web python manage.py createsuperuser
```

Приложение будет доступно по адресу http://127.0.0.1:8000/. Nginx проксирует приложение и обслуживает фотографии из `/media/` при `DEBUG=False`.

Остановка:

```bash
docker compose -f docker/docker-compose.yml down
```

## Локальный запуск через venv

Требования: Python 3.10+ и запущенный PostgreSQL.

```bash
python -m venv .venv
```

Активация в Linux/macOS:

```bash
source .venv/bin/activate
```

Активация в Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Установка и запуск:

```bash
python -m pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py loaddata equipment rooms
python manage.py createsuperuser
python manage.py runserver
```

Для локального запуска оставьте `DB_HOST=localhost`. Docker Compose самостоятельно заменяет его на `db` внутри контейнера приложения.

## Тесты

Локально:

```bash
python manage.py test
```

В Docker:

```bash
docker compose -f docker/docker-compose.yml exec web python manage.py test
```

## Переменные окружения

- `SECRET_KEY` — секретный ключ Django; при `DEBUG=False` должен отличаться от значения по умолчанию.
- `DEBUG` — режим разработки (`True` или `False`).
- `ALLOWED_HOSTS` — разрешённые хосты через запятую.
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` — подключение к PostgreSQL.

## Документация

- Модели: `User`, `Room`, `Booking`, `Equipment`; используются ForeignKey и ManyToManyField.
- Схема БД: `ER_diagram.drawio`.
- Декомпозиция: `DECOMPOSITION.md`.
