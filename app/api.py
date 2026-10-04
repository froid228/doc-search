from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps import get_search_index, get_session
from app.models import Document
from app.schemas import DocumentOut
from app.search import SearchIndex

router = APIRouter(prefix="/documents", tags=["documents"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SearchIndexDep = Annotated[SearchIndex, Depends(get_search_index)]


@router.get(
    "/search",
    response_model=list[DocumentOut],
    summary="Поиск документов по тексту",
    description=(
        "Ищет документы по тексту в поисковом индексе и возвращает первые 20 найденных "
        "со всеми полями из БД, упорядоченные по дате создания."
    ),
)
async def search_documents(
    session: SessionDep,
    search_index: SearchIndexDep,
    q: Annotated[str, Query(min_length=1, description="Произвольный текстовый запрос")],
) -> list[Document]:
    ids = await search_index.search(q, size=settings.search_limit)
    if not ids:
        return []
    result = await session.scalars(
        select(Document).where(Document.id.in_(ids)).order_by(Document.created_date, Document.id)
    )
    return list(result)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удаление документа",
    description="Удаляет документ из БД и из поискового индекса по полю id.",
    responses={404: {"description": "Документ не найден"}},
)
async def delete_document(
    document_id: int,
    session: SessionDep,
    search_index: SearchIndexDep,
) -> Response:
    document = await session.get(Document, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    # Сначала индекс: если упадёт БД, документ останется в базе и пропадёт только из поиска,
    # а не наоборот (поиск всё равно отдаёт только то, что есть в БД).
    await search_index.delete(document_id)
    await session.delete(document)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
