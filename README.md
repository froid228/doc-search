# Document search

Простой поисковик по текстам документов: данные хранятся в PostgreSQL, поисковый индекс — в Elasticsearch.

Стек: Python 3.12, FastAPI, SQLAlchemy 2 (async) + asyncpg, Elasticsearch 8 (async-клиент), Docker.

## Запуск

Нужны Docker и Docker Compose.

```bash
docker compose up --build
```

При старте контейнер приложения сам создаёт таблицу и индекс, загружает `data/posts.csv` (1500 документов) в БД
и индексирует их в Elasticsearch. Повторный запуск данные не дублирует.

После старта:

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs

Остановить и удалить данные: `docker compose down -v`.

Если порт `5432` уже занят локальным PostgreSQL, задайте другой порт для БД на хосте:
`POSTGRES_PORT=5434 docker compose up --build` (приложение внутри Docker это не затрагивает).

## API

Полное описание в формате OpenAPI — в [docs.json](docs.json).

### Поиск

```bash
curl "http://localhost:8000/documents/search?q=конкурс"
```

Запрос ищется по полю `text` в индексе. Из Elasticsearch берутся 20 самых релевантных документов,
затем по их `id` из БД достаются все поля, и результат сортируется по `created_date` (от старых к новым).

```json
[
  {
    "id": 2,
    "rubrics": ["VK-1603736028819866", "VK-95883495386", "VK-55347043459"],
    "text": "🎁 Конкурс на НОВЫЙ СКИН ‼️ ...",
    "created_date": "2019-05-31T17:18:42"
  }
]
```

### Удаление

```bash
curl -X DELETE "http://localhost:8000/documents/2"
```

Удаляет документ из БД и из индекса. Ответ `204`, если документ удалён, `404` — если документа с таким `id` нет.

## Структура данных

Таблица `documents` в БД:

| Поле           | Тип         | Описание               |
|----------------|-------------|------------------------|
| `id`           | `integer`   | первичный ключ         |
| `rubrics`      | `varchar[]` | массив рубрик          |
| `text`         | `text`      | текст документа        |
| `created_date` | `timestamp` | дата создания документа |

Индекс `documents` в Elasticsearch: `id` (id из базы) и `text` (с анализатором `russian`).

## Тесты

Функциональные тесты ходят в API через HTTP-клиент. Им не нужны запущенные PostgreSQL и Elasticsearch:
база подменяется на SQLite в памяти, а индекс — на простую реализацию в памяти.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

## Локальный запуск без Docker для приложения

```bash
docker compose up -d db elastic      # только БД и Elasticsearch
pip install -r requirements.txt
cp .env.example .env
python -m app.load_data              # создать таблицу, индекс и загрузить данные
uvicorn app.main:app --reload
```

Настройки читаются из переменных окружения или `.env` (см. [.env.example](.env.example)).

Обновить `docs.json` после изменения API: `python -m scripts.export_openapi`.

## Структура проекта

```
app/
  main.py        — приложение FastAPI, подключения к БД и Elasticsearch
  api.py         — эндпоинты поиска и удаления
  models.py      — модель таблицы documents
  schemas.py     — схема ответа
  search.py      — работа с индексом Elasticsearch
  load_data.py   — загрузка CSV в БД и индексация
  config.py      — настройки
tests/           — функциональные тесты
data/posts.csv   — тестовый массив данных
docs.json        — OpenAPI-документация
```
