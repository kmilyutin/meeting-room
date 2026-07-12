# Booked! >>>

Сервис для быстрого поиска и бронирования переговорных комнат.

## Как развернуть проект

### 1. **Клонировать репозиторий**
   ```bash
   git clone <ссылка>
   cd <название_проекта>
   ```

### 2. **Настроить переменные окружения**
   Скопируйте пример файла конфигурации и отредактируйте .env, указав свои данные для PostgreSQL:
   ```bash
   cp .env.example .env
   ```

### 3. **Запустить проект через Docker:**
   ```bash
   Bashdocker-compose -f docker/docker-compose.yml up --build
   ```

### 4. **Выполнить миграции:**
   ```bash
   Bashdocker-compose -f docker/docker-compose.yml exec web python manage.py migrate
   ```

### 5. **Создать суперпользователя:**
   ```bash
   Bashdocker-compose -f docker/docker-compose.yml exec web python manage.py createsuperuser
   ```

## Как запустить тесты
   ```bash
   docker-compose -f docker/docker-compose.yml exec web pytest
   ```


## Документация

- Модели: Проект использует 4 модели: User, Room, Booking, Equipment, связанные через ForeignKey и ManyToManyField.
- Схема БД: См. файл ER_diagram.drawio.
- Декомпозиция: См. файл DECOMPOSITION.md.
