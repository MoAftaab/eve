from math import ceil

from fastapi import HTTPException, Query, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


def pagination_params(
    page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100)
) -> tuple[int, int]:
    return page, page_size


def page_query(db: Session, query: Select, page: int, page_size: int):
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return items, {
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": ceil(total / page_size) if total else 0,
    }


def not_found(entity: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity} not found")
