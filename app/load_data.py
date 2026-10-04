"""Создаёт таблицу и индекс, загружает документы из CSV в БД и индексирует их в Elasticsearch.

Запуск: python -m app.load_data
Повторный запуск безопасен: CSV загружается только в пустую БД,
индекс перестраивается только если количество документов в нём расходится с БД.
"""

import ast
import asyncio
import csv
import logging
from datetime import datetime

from elasticsearch import AsyncElasticsearch
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models import Base, Document
from app.search import SearchIndex

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


def read_csv(path: str) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as file:
        return [
            {
                "text": row["text"],
                "created_date": datetime.strptime(row["created_date"], "%Y-%m-%d %H:%M:%S"),
                "rubrics": ast.literal_eval(row["rubrics"]),
            }
            for row in csv.DictReader(file)
        ]


async def load_csv_to_db(session: AsyncSession, path: str) -> None:
    rows = read_csv(path)
    for start in range(0, len(rows), BATCH_SIZE):
        await session.execute(insert(Document), rows[start : start + BATCH_SIZE])
    await session.commit()
    logger.info("Loaded %d documents into the database", len(rows))


async def reindex(session: AsyncSession, search_index: SearchIndex) -> None:
    result = await session.execute(select(Document.id, Document.text))
    await search_index.bulk_index((doc_id, text) for doc_id, text in result)
    logger.info("Search index rebuilt")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    engine = create_async_engine(settings.database_url)
    elastic = AsyncElasticsearch(settings.elastic_url)
    search_index = SearchIndex(elastic, settings.elastic_index)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await search_index.ensure_index()

        async with async_sessionmaker(engine)() as session:
            db_count = await session.scalar(select(func.count()).select_from(Document))
            if db_count == 0:
                await load_csv_to_db(session, settings.csv_path)
                db_count = await session.scalar(select(func.count()).select_from(Document))
            if await search_index.count() != db_count:
                await reindex(session, search_index)
    finally:
        await elastic.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
