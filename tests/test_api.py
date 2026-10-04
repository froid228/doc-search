from datetime import datetime, timedelta

from app.models import Document

START = datetime(2020, 1, 1, 12, 0, 0)


async def test_search_returns_all_db_fields(client, add_documents):
    await add_documents((1, "Привет, мир", START))

    response = await client.get("/documents/search", params={"q": "привет"})

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "rubrics": ["rubric-1", "rubric-2"],
            "text": "Привет, мир",
            "created_date": "2020-01-01T12:00:00",
        }
    ]


async def test_search_returns_only_matching_documents(client, add_documents):
    await add_documents((1, "красный трамвай", START), (2, "зелёный автобус", START))

    response = await client.get("/documents/search", params={"q": "трамвай"})

    assert [doc["id"] for doc in response.json()] == [1]


async def test_search_orders_by_created_date(client, add_documents):
    await add_documents(
        (1, "новость третья", START + timedelta(days=2)),
        (2, "новость первая", START),
        (3, "новость вторая", START + timedelta(days=1)),
    )

    response = await client.get("/documents/search", params={"q": "новость"})

    assert [doc["id"] for doc in response.json()] == [2, 3, 1]


async def test_search_returns_at_most_20_documents(client, add_documents):
    await add_documents(*((i, f"пост номер {i}", START + timedelta(hours=i)) for i in range(1, 31)))

    response = await client.get("/documents/search", params={"q": "пост"})

    dates = [doc["created_date"] for doc in response.json()]
    assert len(dates) == 20
    assert dates == sorted(dates)


async def test_search_without_matches_returns_empty_list(client, add_documents):
    await add_documents((1, "красный трамвай", START))

    response = await client.get("/documents/search", params={"q": "самолёт"})

    assert response.status_code == 200
    assert response.json() == []


async def test_search_requires_query(client):
    assert (await client.get("/documents/search")).status_code == 422
    assert (await client.get("/documents/search", params={"q": ""})).status_code == 422


async def test_delete_removes_document_from_db_and_index(client, add_documents, session_factory, search_index):
    await add_documents((1, "красный трамвай", START), (2, "синий трамвай", START))

    response = await client.delete("/documents/1")

    assert response.status_code == 204
    async with session_factory() as session:
        assert await session.get(Document, 1) is None
        assert await session.get(Document, 2) is not None
    assert list(search_index.documents) == [2]

    response = await client.get("/documents/search", params={"q": "трамвай"})
    assert [doc["id"] for doc in response.json()] == [2]


async def test_delete_missing_document_returns_404(client):
    response = await client.delete("/documents/999")

    assert response.status_code == 404


async def test_delete_twice_returns_404(client, add_documents):
    await add_documents((1, "красный трамвай", START))

    assert (await client.delete("/documents/1")).status_code == 204
    assert (await client.delete("/documents/1")).status_code == 404
