# Локальное развёртывание (1 компания)

Цель: запуск “на своём ноутбуке” без DevOps и без enterprise‑усложнений.

## Быстрый старт (Windows)

Backend:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

## Docker (опционально)

```powershell
copy .env.example .env
docker compose up --build
```

## Локальные режимы

- **local-only mode**: настройки фронтенда хранятся локально (LocalStorage). Рекомендован для 1 компании.
- **demo mode**: режим демонстрации без “внутренних ops” страниц по умолчанию.

