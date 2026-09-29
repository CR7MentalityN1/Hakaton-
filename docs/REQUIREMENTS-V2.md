# Матрица расширенного задания

Исходный PDF перечитан полностью; его требования сохраняются. Сообщение пользователя расширяет стек, структуру, модель и критерии готовности, не отменяя PNG/PDF диаграммы, JSON-экспорт, встроенную документацию со скриншотами и презентацию PDF. Старый прототип сохранён в `.archive/initial-prototype.zip`.

- [x] React TypeScript Vite Router Query Axios MUI Recharts; Vitest/RTL, ESLint/Prettier.
- [x] FastAPI SQLAlchemy Pydantic PostgreSQL; Alembic upgrade/downgrade, без create_all на старте.
- [x] Нормализованные университеты, направления, программы, продукты, сотрудники, контакты, взаимодействия, workflow/stages/transitions, comments, attachments, audit.
- [x] Keycloak realm rostelecom-it-school, clients crm-frontend/crm-backend; PKCE и JWT; admin/manager/user; demo passwords.
- [x] Разграничение на сервере по назначениям и подчинённым; немедленный отзыв прав.
- [x] CRUD/поиск/сортировка/пагинация; карточка вуза с контактами, программами, лицензиями и взаимодействиями.
- [x] 14 базовых этапов, редактирование/порядок/отключение; переходы с from/to/actor/time/comment; timeline.
- [x] Файлы вне БД, Storage abstraction, MIME/сигнатуры/размер env/path traversal.
- [x] Excel preview/маппинг/import с created/updated/skipped/errors, все поля PDF.
- [x] Report preview, XLS/XLSX/PDF/JSON; период, фильтры, дата и выбранные колонки.
- [x] Dashboard: карточки, пять реальных графиков, семь фильтров; графики PNG/PDF.
- [x] LMSClient/WebsiteClient + mocks и реальные HTTP adapters; идемпотентная синхронизация/аудит.
- [x] Redis: каталоги/dashboard, изоляция по scope, инвалидация после записи; права без кэширования.
- [x] Audit old/new, UI; Settings; AIWorkflowAssistant без внешнего AI.
- [x] Responsive layout, skeleton/error/empty/success/confirm/validation/403/404/error boundary.
- [x] /api/v1, /docs, /openapi.json: схемы, описания, response models, единые ошибки code/message/details.
- [x] Security: JWT/RBAC/scope/CORS/headers/ORM/секреты; честная карта ИБ без заявления сертификации.
- [x] Seed: 15 вузов, 5 направлений, 10 программ, 8 продуктов, 5 менеджеров, 30+ взаимодействий.
- [x] Compose frontend/backend/postgres/redis/keycloak; 3000/8000/8080; volumes/healthchecks/env.
- [x] pytest auth/roles/CRUD/interactions/workflow/reports/import/filters; frontend smoke; lint/types/build.
- [x] Документы USER_GUIDE/ADMIN_GUIDE/ARCHITECTURE/API/SECURITY/DEPLOYMENT/PRESENTATION, Mermaid, Archi, встроенные HTML/PDF/скриншоты.
- [ ] SLA ≤1 с при 50 параллельных пользователях: выполнены 50 конкурентных запросов и 10 отчётов без ошибок, но p95 запросов 1,34 с. Целевой прогон остаётся.

Ограничение среды на старте: Docker Desktop/Engine и WSL отсутствуют. Запуск контейнеров нельзя считать пройденным по статической конфигурации. Все доступные проверки выполняются независимо от этого ограничения.


Отметка реализации Compose не означает успешную сборку контейнеров. Docker build заблокирован отсутствием Engine; полноценный контейнерный DoD остаётся открытым. См. ACCEPTANCE.md и CHECKLIST.md.
