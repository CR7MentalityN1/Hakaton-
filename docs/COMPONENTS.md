# Компоненты и библиотеки

Прямые зависимости frontend зафиксированы в package-lock.json; backend — в requirements. Транзитивные пакеты входят в дерево соответствующего менеджера.

## Frontend

- react: 19.2.4
- react-dom: 19.2.4
- react-router-dom: 7.13.1
- @tanstack/react-query: 5.90.21
- axios: 1.13.6
- @mui/material: 7.3.9
- @mui/icons-material: 7.3.9
- @emotion/react: 11.14.0
- @emotion/styled: 11.14.1
- recharts: 3.7.0
- keycloak-js: 26.2.3
- @types/react: 19.2.14
- @types/react-dom: 19.2.3
- @vitejs/plugin-react: 5.1.4
- vite: 7.3.1
- typescript: 5.9.3
- vitest: 3.2.4
- jsdom: 26.1.0
- @testing-library/react: 16.3.2
- @testing-library/jest-dom: 6.9.1
- @testing-library/user-event: 14.6.1
- eslint: 9.39.4
- @eslint/js: 9.39.4
- typescript-eslint: 8.56.1
- eslint-plugin-react-hooks: 7.0.1
- eslint-plugin-react-refresh: 0.5.2
- globals: 17.4.0

## Backend

fastapi==0.135.1
uvicorn==0.42.0
SQLAlchemy==2.0.48
alembic==1.18.4
psycopg[binary]==3.3.3
pydantic-settings==2.13.1
PyJWT[crypto]==2.12.1
redis==7.3.0
python-multipart==0.0.22
openpyxl==3.1.5
xlrd==2.0.2
xlwt==1.3.0
reportlab==4.4.10
matplotlib==3.10.8
httpx==0.28.1


## Backend tests

-r requirements.txt
pytest==9.0.2
fakeredis==2.34.1
ruff==0.15.6
PyYAML==6.0.3


## Infrastructure

PostgreSQL 17, Redis 7, Keycloak 26.2.5, Nginx 1.28, Python 3.12, Node 24. Для production следует фиксировать digest образов после проверки обновлений.
