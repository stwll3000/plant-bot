# 🪴 Семейный трекер полива растений

Telegram-бот с Mini App: семья ведёт общий сад, видит, кто и когда поливал
каждое растение, и получает напоминания, когда наступает срок полива.

**Стек:** Python 3.12, aiogram 3, FastAPI, PostgreSQL, SQLAlchemy 2 (async),
Alembic, APScheduler. Деплой — Railway.

## Структура

```
app/
├── main.py        # точка входа: бот + веб-сервер + планировщик
├── config.py      # настройки из переменных окружения
├── bot/           # хендлеры aiogram: онбординг, полив из чата, фото
├── web/           # FastAPI: REST API + статика Mini App
├── db/            # модели SQLAlchemy и репозитории (запросы к БД)
├── services/      # бизнес-логика, общая для бота и API
└── scheduler/     # задача рассылки напоминаний
alembic/           # миграции
```

## Запуск локально

1. Установи Python 3.12+ и PostgreSQL (или подними его в Docker):
   ```bash
   docker run -d --name plantbot-pg -p 5432:5432 \
     -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=plantbot postgres:16
   ```

2. Создай виртуальное окружение и поставь зависимости:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Создай бота у [@BotFather](https://t.me/BotFather) (`/newbot`) и получи токен.

4. Скопируй `.env.example` в `.env` и заполни `BOT_TOKEN` и `DATABASE_URL`.
   `WEBAPP_URL` локально можно оставить пустым — кнопка Mini App
   просто не появится (Telegram требует HTTPS).

5. Применяй миграции и запускай:
   ```bash
   alembic upgrade head
   python -m app.main
   ```

Бот работает через long polling — публичный адрес для него не нужен.
Mini App локально можно открыть в браузере: http://localhost:8000
(но авторизация заработает только внутри Telegram).

## Деплой на Railway

1. Запушь проект в GitHub-репозиторий.
2. В Railway: **New Project → Deploy from GitHub repo**.
3. Добавь в проект Postgres: **Create → Database → PostgreSQL**.
4. В настройках сервиса приложения → **Variables** добавь:
   - `BOT_TOKEN` — токен от BotFather
   - `DATABASE_URL` — reference на переменную Postgres:
     `${{Postgres.DATABASE_URL}}`
   - `WEBAPP_URL` — публичный домен сервиса (см. шаг 5)
5. В **Settings → Networking** нажми **Generate Domain** — получишь адрес
   вида `https://<имя>.up.railway.app`. Впиши его в `WEBAPP_URL`.
6. При деплое Railway выполнит `alembic upgrade head && python -m app.main`
   (задано в `railway.json`) — миграции применятся автоматически.
7. Проверь: открой бота, нажми `/start`, создай семью и открой «🪴 Открыть сад».

## Как пользоваться

- `/start` — создать семью или вступить по коду/ссылке-приглашению
- **🪴 Открыть сад** — Mini App: дома → комнаты → растения, отметка полива
- **📖 Последние поливы** или `/log` — общий журнал семьи
- Пришли боту **фото** — он предложит привязать его к растению
- Когда наступит срок полива, бот пришлёт напоминание всем в семье
  с кнопкой «💧 Полил(а)»

## Что заложено на вторую итерацию

Типы ухода вынесены в справочник `care_types`, расписания — в
`plant_care_schedules` (по одному на тип ухода), журнал `care_logs` хранит
тип ухода. Подкормка/опрыскивание/пересадка, статистика, стрики и
отключение уведомлений по конкретному дому добавляются без переделки схемы.
