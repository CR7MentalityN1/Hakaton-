# ИТ Школа Ростелеком — CRM

Учебное production-like full-stack приложение по оригинальному PDF «Система контроля и обработки статистических данных по обучению студентов ВУЗов и школ по ИТ направлениям». Исходное ТЗ находится в корне; матрица требований — [docs/REQUIREMENTS-V2.md](docs/REQUIREMENTS-V2.md), фактические результаты — [docs/ACCEPTANCE.md](docs/ACCEPTANCE.md).

Реализованы ВУЗы и контакты, справочники направлений/программ/продуктов, взаимодействия и редактируемые workflow, назначения сотрудников, комментарии, файлы, история, аудит, аналитика и рейтинг программ, Excel import preview/mapping, отчёты XLSX/XLS/PDF/JSON, диаграммы PNG/PDF, LMS/Website adapters и локальный помощник по правилам.

## Запуск на текущем Windows-компьютере без Docker

Запустите **`start-local.bat`** в корне проекта. Он использует уже подготовленные portable PostgreSQL/Java/Keycloak в `.runtime`, зависимости Python в `.tools` и собранный frontend. Проверяет миграции, авторизацию и API-прокси; повторный запуск использует работающие сервисы. Ничего не устанавливает в Windows. Адрес CRM: http://localhost:3000, вход `admin / admin123`.

Если Redis недоступен, CRM работает с прямыми запросами к БД, а `/health` сообщает `redis: degraded`. Логи запущенных сценарием процессов: `.runtime/logs`. Портативные бинарные файлы и локальная БД не входят в исходники: на другом компьютере используйте инструкцию [разработки без Docker](docs/DEPLOYMENT.md#разработка-без-docker).

## Запуск через Docker Compose

Для публичной ссылки жюри подготовлен отдельный HTTPS-вариант: [PUBLIC_DEMO.md](docs/PUBLIC_DEMO.md). Он использует Linux-сервер, два DNS-имени, Caddy и уникальные пароли. Фактическая публикация требует выбранного сервера и доступа к нему; публичный URL пока не создан.

**Docker Compose подготовлен, но интеграционный запуск контейнеров на этой машине не выполнялся из-за системного ограничения Windows.** Dockerfile и Compose проверены статически; это не подтверждение успешной сборки контейнеров. По текущему решению Docker и WSL2 локально не устанавливаются. PostgreSQL, Keycloak, backend и frontend проверяются отдельно без Docker.

Требуются Docker Engine + Compose v2 (или Docker Desktop с Linux containers), свободные порты 3000, 8000, 8080 и интернет для первой сборки. Рекомендуемый стартовый ресурс: 4 CPU / 8 ГБ RAM.

```bash
docker compose up --build -d
docker compose ps
```

На Windows альтернативно запустите `start.bat`: он выполнит сборку и проверит healthchecks, подключение к настоящему Redis и версию миграции. Docker Desktop/Engine должен быть установлен и запущен заранее.

До первого запуска можно скопировать `.env.example` в `.env`. В PowerShell: `Copy-Item .env.example .env`. Демонстрационные defaults позволяют запустить и без `.env`.

| Сервис | Адрес |
|---|---|
| CRM | http://localhost:3000 |
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| OpenAPI | http://localhost:8000/openapi.json |
| Keycloak | http://localhost:8080 |
| Встроенная документация | http://localhost:3000/handbook/ |

Запуск backend выполняет `alembic upgrade head`, затем идемпотентный seed. База и файлы сохраняются в volumes. Остановка без удаления данных: `docker compose down`. Логи: `docker compose logs -f backend keycloak`. При конфликте портов используйте FRONTEND_PORT/BACKEND_PORT/KEYCLOAK_PORT; изменение frontend URL требует обновить redirectUris/webOrigins Keycloak, подробнее [DEPLOYMENT](docs/DEPLOYMENT.md).

## Демопользователи

| Логин | Пароль | Роль |
|---|---|---|
| admin | admin123 | Администратор CRM |
| manager | manager123 | Руководитель |
| user | user123 | КАМ, менеджер по ВУЗам |
| user2 … user5 | user2123 … user5123 | Ещё четыре КАМа |

Keycloak realm: `rostelecom-it-school`; clients `crm-frontend`, `crm-backend`. Системная консоль Keycloak: `bootstrap-admin` / `change-me-local-demo` (меняются KC_ADMIN/KC_ADMIN_PASSWORD). **Перед production смените все демонстрационные пароли**, уберите фикстуры, настройте HTTPS и production Keycloak. Реализованные меры и оставшиеся организационные/инфраструктурные задачи описаны в [SECURITY](docs/SECURITY.md). Заявления о сертификации ФСТЭК нет.

Seed: 15 ВУЗов, 5 направлений, 10 программ, 8 продуктов, 5 КАМов, 1 руководитель, 1 администратор и 45 взаимодействий. Все контакты и статистика синтетические. По оригинальному PDF менеджер по ВУЗам — роль USER, а MANAGER — его руководитель.

## Архитектура и структура

Frontend: React 19, TypeScript, Vite, Router, TanStack Query, Axios, MUI, Recharts. Backend: Python 3.12+, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL. Keycloak обеспечивает OIDC Code Flow + PKCE и JWT, Redis — кэш, volume — файлы. Заменяемые FileStorage, LMSClient, WebsiteClient и AIWorkflowAssistant отделены от бизнес-логики.

```text
frontend/src/      интерфейс, страницы, компоненты, API, auth, layouts
backend/app/       api, core, db, models, schemas, services,
                   repositories, integrations, security, reports
backend/alembic/   миграции
backend/tests/     pytest: auth, scope, CRUD, workflow, files, imports, reports
docker/           realm import, PostgreSQL init, Nginx
docs/             руководства, схемы, PDF, презентация, результаты проверок
scripts/          генерация документации, браузерная и нагрузочная проверки
docker-compose.yml
```

Полный перечень прямых библиотек и версий — [COMPONENTS](docs/COMPONENTS.md), frontend lock — package-lock.json, backend зависимости — backend/requirements.txt и requirements-dev.txt. Исходники открыты для чтения и не обфусцированы; минификация применяется только к сборке браузера.

## Разработка и проверки

Для локальной разработки нужны Python 3.12+ и Node 22.12+/24, PostgreSQL, Redis и Keycloak с импортированным realm.

```bash
python -m venv .venv
# Linux: source .venv/bin/activate
# Windows: .venv\Scripts\Activate.ps1
pip install -r backend/requirements-dev.txt
npm ci
# Задайте PYTHONPATH=backend и переменные из .env.example
alembic -c backend/alembic.ini upgrade head
python -m app.db.seed
uvicorn app.main:app --host 127.0.0.1 --port 8000
# Во втором терминале:
npm run dev
```

```bash
pytest backend/tests -q
ruff check backend/app backend/alembic backend/tests
ruff format --check backend/app backend/alembic backend/tests
npm test
npm run lint
npm run typecheck
npm run build
```

Backend-тесты по умолчанию используют SQLite. Для PostgreSQL задайте TEST_DATABASE_URL с **отдельной тестовой БД**: fixture выполняет downgrade до base. Реальный браузерный тест: `node scripts/browser-smoke.mjs` (требуется Edge и запущенные сервисы). Нагрузка: `node scripts/load-check.mjs`. PDF/HTML/Archi: `python scripts/build_docs.py` с установленными backend-зависимостями и PYTHONPATH=backend.

## Миграции

```bash
alembic -c backend/alembic.ini revision --autogenerate -m "change_description"
alembic -c backend/alembic.ini upgrade head
alembic -c backend/alembic.ini downgrade -1
# В запущенном контейнере:
docker compose exec backend alembic current
```

Перед rollback сделайте backup; initial downgrade удаляет таблицы CRM. Схема Keycloak управляется самим Keycloak.

## Документация и ограничения

- [Руководство пользователя](docs/USER_GUIDE.md), [администратора](docs/ADMIN_GUIDE.md).
- [Архитектура и Mermaid](docs/ARCHITECTURE.md), [API](docs/API.md), [развёртывание](docs/DEPLOYMENT.md).
- [Презентация: 12 слайдов](docs/PRESENTATION.md), PDF: docs/PRESENTATION.pdf.
- [Archi-модель](docs/architecture.archimate), [сопроводительная документация PDF](docs/documentation.pdf).
- [Приёмка и ограничения проверок](docs/ACCEPTANCE.md).

В исходной Windows-среде отсутствует Docker Engine. Compose config проверен, но сборка/запуск Linux-контейнеров требуют отдельной проверки на Docker-хосте. Реальные Keycloak и PostgreSQL запускались portable-процессами для проверки входа, миграций и API. Redis в автоматических backend-тестах заменён fakeredis; отказ кэша не блокирует работу. Контракты реальных LMS/сайта заказчик пока не предоставил. Нагрузочные замеры относятся к демонстрационным данным, не гарантируют SLA на production. URL публичного репозитория и опубликованного стенда появятся после размещения заказчиком; локальные файлы не выданы за публичные ссылки.
