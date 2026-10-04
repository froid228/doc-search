from collections.abc import Iterable

from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_bulk

INDEX_BODY = {
    "settings": {"number_of_shards": 1, "number_of_replicas": 0},
    "mappings": {
        "properties": {
            "id": {"type": "long"},
            "text": {"type": "text", "analyzer": "russian"},
        }
    },
}


class SearchIndex:
    """Поисковый индекс документов в Elasticsearch (поля id и text)."""

    def __init__(self, client: AsyncElasticsearch, index: str) -> None:
        self._client = client
        self._index = index

    async def ensure_index(self) -> None:
        if not await self._client.indices.exists(index=self._index):
            await self._client.indices.create(index=self._index, **INDEX_BODY)

    async def count(self) -> int:
        await self._client.indices.refresh(index=self._index)
        result = await self._client.count(index=self._index)
        return result["count"]

    async def bulk_index(self, documents: Iterable[tuple[int, str]]) -> None:
        actions = (
            {"_index": self._index, "_id": doc_id, "_source": {"id": doc_id, "text": text}}
            for doc_id, text in documents
        )
        await async_bulk(self._client, actions)

    async def search(self, query: str, size: int) -> list[int]:
        result = await self._client.search(
            index=self._index,
            query={"match": {"text": query}},
            size=size,
            source=["id"],
        )
        return [hit["_source"]["id"] for hit in result["hits"]["hits"]]

    async def delete(self, doc_id: int) -> None:
        try:
            # refresh="wait_for": ответ приходит, когда удаление уже видно в поиске,
            # иначе удалённый id ещё ~1с попадает в топ-20 и выдача становится короче.
            await self._client.delete(index=self._index, id=str(doc_id), refresh="wait_for")
        except NotFoundError:
            pass
