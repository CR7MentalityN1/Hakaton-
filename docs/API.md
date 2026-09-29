# API

Base URL: http://localhost:8000/api/v1. Интерактивное описание: `/docs`, OpenAPI: `/openapi.json`; снимок схемы приложен как `openapi.json`. Все защищённые запросы требуют `Authorization: Bearer <access_token>`. RS256, issuer и audience проверяются по JWKS Keycloak. API не принимает пароль.

## Группы методов

| Методы | Путь | Назначение |
|---|---|---|
| GET | /auth/config, /auth/me | OIDC конфигурация, текущий сотрудник |
| GET, POST | /universities | Список и создание |
| GET, PUT, DELETE | /universities/{id} | Карточка, изменение, удаление |
| PUT | /universities/{id}/assignments | Назначения сотрудников |
| GET, POST | /universities/{id}/contacts | Контакты |
| PUT, DELETE | /universities/{id}/contacts/{cid} | Изменение контакта |
| GET, POST | /directions, /programs, /products | Справочники |
| GET, PUT, DELETE | /directions/{id}, /programs/{id}, /products/{id} | Запись справочника |
| GET, POST | /users | Сотрудники / регистрация |
| PUT | /users/{id} | Роль, руководитель, блокировка |
| GET, POST | /workflows | Шаблоны процессов |
| PUT | /workflows/{id} | Шаблон и этапы |
| GET, POST | /interactions | Взаимодействия |
| GET, PUT, DELETE | /interactions/{id} | Карточка, правка с version, удаление |
| GET | /interactions/{id}/allowed-stages | Разрешённые переходы |
| POST | /interactions/{id}/transition | Переход: to_stage_id, version, comment |
| GET | /interactions/{id}/timeline | История |
| GET, POST | /interactions/{id}/comments | Комментарии этапа |
| GET, POST | /interactions/{id}/attachments | Файлы: multipart file, stage_id |
| GET | /attachments/{id}/download | Защищённая загрузка |
| GET | /interactions/{id}/advice | Рекомендации |
| GET | /dashboard | Агрегаты и пять графиков |
| GET | /dashboard/chart/{png или pdf} | Диаграмма рейтинга |
| POST | /reports/preview, /reports/export | Отчёт с фильтрами и columns |
| GET | /import/template | XLSX шаблон |
| POST | /import/preview, /import/commit | XLS/XLSX анализ и импорт |
| GET | /integrations | Статусы адаптеров |
| GET | /integrations/{lms или website}/mock-data | Тестовый JSON |
| POST | /integrations/{lms или website}/sync | Синхронизация |
| GET | /audit | Журнал администратора |
| GET, PUT | /settings | Настройки |

Системный `/health` возвращает состояние БД, кэша и режим auth; без БД — 503, без Redis — degraded с работой без кэша. Документация доступна через `/handbook/`.

## Форматы и фильтры

Пагинация: page от 1, page_size от 1 до 1000. Ответ `{items,total,page,page_size}`. Общие фильтры: start/end (YYYY-MM-DD), university_id, direction_id, program_id, product_id, responsible_employee_id, stage_id, q. Отчёты принимают те же поля в JSON, columns (ключи колонок) и format xlsx/xls/pdf/json. Даты возвращаются ISO, временные метки — UTC.

Единая ошибка: `{"code":"VERSION_CONFLICT","message":"Запись изменена другим пользователем","details":{}}`. Валидация добавляет details.fields с именем и причиной. Недоступные сущности возвращают 404, чтобы не раскрывать их существование. Все SQL-запросы параметризуются SQLAlchemy.

## Контракт адаптеров

```json
[{"external_id":"lms-1001","university":"Университет ИТМО","direction":"Разработка","program":"Основы Python","product":"РТК Облако","vendor":"Ростелеком","contract_number":"LMS-1001","license_signed":true,"license_end_date":"2027-12-31","transfer_status":"Передано","applications":120,"students":85,"streams":3,"notes":"Демонстрация"}]
```

Не более 10 000 записей и 20 МБ HTTP-ответа. Обязателен external_id; source задаёт маршрут. Каждая строка импортируется с правами инициатора. Параметр workflow_id выбирает шаблон для новых записей. Для существующего взаимодействия workflow не меняется. Итог `{created,updated,skipped,errors:[{row,message}]}` сохраняется в аудите и статусе интеграции.
