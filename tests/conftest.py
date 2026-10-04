from collections.abc import AsyncIterator
from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.deps import get_search_index, get_session
from app.main import app
from app.models import Base, Document


class FakeSearchIndex:
    """Замена Elasticsearch в памяти: документ подходит, если содержит любое слово запроса."""

    def __init__(self) -> None:
        self.documents: dict[int, str] = {}

    async def bulk_index(self, documents) -> None:
        self.documents.update(documents)

    async def search(self, query: str, size: int) -> list[int]:
        words = query.lower().split()
        found = [
            doc_id
            for doc_id, text in self.documents.items()
            if any(word in text.lower() for word in words)
        ]
        return found[:size]

    async def delete(self, doc_id: int) -> None:
        self.documents.pop(doc_id, None)


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
def search_index() -> FakeSearchIndex:
    return FakeSearchIndex()


@pytest.fixture
async def client(session_factory, search_index) -> AsyncIterator[AsyncClient]:
    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_search_index] = lambda: search_index
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


@pytest.fixture
def add_documents(session_factory, search_index):
    async def _add(*documents: tuple[int, str, datetime]) -> None:
        async with session_factory() as session:
            await session.execute(
                insert(Document),
                [
                    {"id": doc_id, "text": text, "created_date": created, "rubrics": ["rubric-1", "rubric-2"]}
                    for doc_id, text, created in documents
                ],
            )
            await session.commit()
        await search_index.bulk_index((doc_id, text) for doc_id, text, _ in documents)

    return _add
