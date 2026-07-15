# Архитектура проекта «Booked!»

Документ содержит схему сервисов (слои приложения) и схему взаимодействия
для ключевого сценария. Схема базы данных — в файле `ER_diagram.drawio` /
`ER_diagram.png`.

## Схема сервисов (слои приложения)

```mermaid
flowchart TB
    subgraph client["Клиент"]
        browser["Браузер<br>HTML + Bootstrap 5"]
    end

    subgraph django["Django-приложение (config, accounts, rooms)"]
        subgraph presentation["Слой представления"]
            urls["URL-маршрутизация<br>config/urls, rooms/urls, accounts/urls"]
            views["Представления<br>rooms.views (поиск, CRUD брони, расписание)<br>accounts.views (регистрация, вход, профиль)<br>RoomListView / RoomDetailView (CBV)"]
            templates["Шаблоны<br>base.html + страницы приложений"]
            adminpanel["Админ-панель<br>управление комнатами и бронями"]
        end

        subgraph business["Слой бизнес-логики"]
            forms["Формы и валидация<br>BookingForm, UserRegistrationForm, ProfileForm"]
            rules["Правила бронирования<br>пересечения, вместимость, доступность,<br>запрет прошедшего времени"]
            schedule["Расписание<br>таймлайн дня, свободные слоты,<br>продление брони"]
            search["Подбор переговорных<br>по дате, времени, участникам, инвентарю"]
        end

        subgraph data["Слой данных"]
            orm["Django ORM<br>User, Room, Equipment, Booking"]
        end
    end

    subgraph infra["Инфраструктура (Docker Compose)"]
        db[("PostgreSQL 15<br>CHECK и EXCLUSION constraints")]
        static["WhiteNoise<br>статические файлы"]
        media["Media<br>изображения комнат"]
    end

    browser -- "HTTP-запрос" --> urls
    urls --> views
    urls --> adminpanel
    views --> forms
    forms --> rules
    views --> schedule
    views --> search
    rules --> orm
    schedule --> orm
    search --> orm
    adminpanel --> orm
    orm --> db
    views --> templates
    templates -- "HTML-ответ" --> browser
    static --> browser
    media --> browser
```

**Описание слоёв:**

| Слой | Ответственность |
|------|-----------------|
| Клиент | Отрисовка страниц (Bootstrap 5), отправка форм и GET-параметров поиска |
| Представление | Маршрутизация URL, обработка запросов, рендер шаблонов, права доступа (`login_required`, фильтр по владельцу брони) |
| Бизнес-логика | Валидация форм, проверка пересечений/вместимости/доступности, построение расписания и свободных слотов, подбор комнат |
| Данные | Django ORM: модели и связи (FK `Booking→User`, `Booking→Room`; M2M `Room↔Equipment`) |
| Инфраструктура | PostgreSQL (ограничения целостности на уровне БД), WhiteNoise для статики, Docker Compose для запуска |

## Схема взаимодействия: сценарий «Создание бронирования»

```mermaid
sequenceDiagram
    actor U as Пользователь
    participant B as Браузер
    participant V as View book_room
    participant F as BookingForm
    participant O as Django ORM
    participant DB as PostgreSQL

    U->>B: Ищет комнату (дата, время, участники, инвентарь)
    B->>V: GET /rooms/{id}/book/?date=...&start_time=...
    Note over V: Проверка авторизации.<br>Гость — редирект на /login/
    V-->>B: Форма бронирования (поля предзаполнены из поиска)
    U->>B: Заполняет название, подтверждает
    B->>V: POST /rooms/{id}/book/
    V->>F: Валидация данных
    F->>O: Есть ли пересекающиеся брони?
    O->>DB: SELECT ... WHERE start_time < конец AND end_time > начало
    DB-->>O: Результат
    alt Данные некорректны или есть конфликт
        F-->>V: Ошибки валидации
        V-->>B: Форма с сообщениями об ошибках
    else Всё корректно
        F-->>V: Данные валидны
        V->>O: Повторная проверка конфликта и сохранение<br>(транзакция + select_for_update)
        O->>DB: INSERT INTO booking (organizer = текущий пользователь)
        Note over DB: EXCLUSION constraint дополнительно<br>запрещает пересечения на уровне БД
        DB-->>O: OK
        V-->>B: Redirect на «Мои бронирования»
        B-->>U: Бронь в списке, интервал занят в расписании комнаты
    end
```
