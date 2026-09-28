from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import db_session, require_admin
from app.api.utils import not_found, page_query, pagination_params
from app.core.cache import cache_delete, cache_get, cache_set
from app.db.models import DiagnosticCentre, DiagnosticTest, User
from app.schemas import (
    CentreCreate,
    CentrePage,
    CentreResponse,
    CentreUpdate,
    TestCreate,
    TestPage,
    TestResponse,
    TestUpdate,
)

router = APIRouter(tags=["catalog"])


@router.get("/centres", response_model=CentrePage)
def list_centres(
    page_data: tuple[int, int] = Depends(pagination_params),
    active_only: bool = Query(default=True),
    db: Session = Depends(db_session),
):
    page, page_size = page_data
    cache_key = f"centres:{page}:{page_size}:{active_only}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    query = select(DiagnosticCentre).order_by(DiagnosticCentre.name)
    if active_only:
        query = query.where(DiagnosticCentre.is_active.is_(True))
    items, meta = page_query(db, query, page, page_size)
    response = {
        "items": [CentreResponse.model_validate(item).model_dump(mode="json") for item in items],
        "meta": meta,
    }
    cache_set(cache_key, response)
    return response


@router.get("/centres/{centre_id}", response_model=CentreResponse)
def get_centre(centre_id: str, db: Session = Depends(db_session)):
    centre = db.get(DiagnosticCentre, centre_id)
    if not centre or not centre.is_active:
        raise not_found("Diagnostic centre")
    return centre


@router.post("/centres", response_model=CentreResponse, status_code=status.HTTP_201_CREATED)
def create_centre(
    payload: CentreCreate, _: User = Depends(require_admin), db: Session = Depends(db_session)
):
    centre = DiagnosticCentre(name=payload.name.strip(), location=payload.location.strip())
    db.add(centre)
    db.commit()
    db.refresh(centre)
    cache_delete("centres:")
    return centre


@router.patch("/centres/{centre_id}", response_model=CentreResponse)
def update_centre(
    centre_id: str,
    payload: CentreUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(db_session),
):
    centre = db.get(DiagnosticCentre, centre_id)
    if not centre:
        raise not_found("Diagnostic centre")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(centre, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(centre)
    cache_delete("centres:")
    return centre


@router.delete("/centres/{centre_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_centre(
    centre_id: str, _: User = Depends(require_admin), db: Session = Depends(db_session)
):
    centre = db.get(DiagnosticCentre, centre_id)
    if not centre:
        raise not_found("Diagnostic centre")
    centre.is_active = False
    db.commit()
    cache_delete("centres:")


@router.get("/tests", response_model=TestPage)
def list_tests(
    page_data: tuple[int, int] = Depends(pagination_params),
    centre_id: str | None = Query(default=None),
    active_only: bool = Query(default=True),
    db: Session = Depends(db_session),
):
    page, page_size = page_data
    cache_key = f"tests:{page}:{page_size}:{centre_id}:{active_only}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    query = select(DiagnosticTest).order_by(DiagnosticTest.name)
    if centre_id:
        query = query.where(DiagnosticTest.centre_id == centre_id)
    if active_only:
        query = query.where(DiagnosticTest.is_active.is_(True))
    items, meta = page_query(db, query, page, page_size)
    response = {
        "items": [TestResponse.model_validate(item).model_dump(mode="json") for item in items],
        "meta": meta,
    }
    cache_set(cache_key, response)
    return response


@router.get("/tests/{test_id}", response_model=TestResponse)
def get_test(test_id: str, db: Session = Depends(db_session)):
    test = db.get(DiagnosticTest, test_id)
    if not test or not test.is_active:
        raise not_found("Diagnostic test")
    return test


@router.post("/tests", response_model=TestResponse, status_code=status.HTTP_201_CREATED)
def create_test(
    payload: TestCreate, _: User = Depends(require_admin), db: Session = Depends(db_session)
):
    if not db.get(DiagnosticCentre, payload.centre_id):
        raise not_found("Diagnostic centre")
    test = DiagnosticTest(**payload.model_dump())
    db.add(test)
    db.commit()
    db.refresh(test)
    cache_delete("tests:")
    return test


@router.patch("/tests/{test_id}", response_model=TestResponse)
def update_test(
    test_id: str,
    payload: TestUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(db_session),
):
    test = db.get(DiagnosticTest, test_id)
    if not test:
        raise not_found("Diagnostic test")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(test, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(test)
    cache_delete("tests:")
    return test


@router.delete("/tests/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test(test_id: str, _: User = Depends(require_admin), db: Session = Depends(db_session)):
    test = db.get(DiagnosticTest, test_id)
    if not test:
        raise not_found("Diagnostic test")
    test.is_active = False
    db.commit()
    cache_delete("tests:")
