from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api import router
from app.config import settings
from app.search import SearchIndex


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = create_async_engine(settings.database_url)
    elastic = AsyncElasticsearch(settings.elastic_url)
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.search_index = SearchIndex(elastic, settings.elastic_index)
    yield
    await elastic.close()
    await engine.dispose()


app = FastAPI(
    title="Document search",
    description="Простой поисковик по текстам документов.",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(router)
