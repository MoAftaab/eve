from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import db_session
from app.core.security import hash_password
from app.db.models import DiagnosticCentre, DiagnosticTest, User
from app.db.session import Base
from app.main import app


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()

    def override() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[db_session] = override
    try:
        yield session
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db: Session) -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def seed(db: Session) -> dict[str, str]:
    admin = User(
        email="admin@example.com",
        full_name="EVE Admin",
        password_hash=hash_password("AdminPass123"),
        role="ADMIN",
    )
    user = User(
        email="user@example.com",
        full_name="Test Patient",
        password_hash=hash_password("PatientPass123"),
    )
    centre = DiagnosticCentre(name="Wellness Diagnostics", location="12 Green Avenue")
    db.add_all([admin, user, centre])
    db.flush()
    test = DiagnosticTest(
        centre_id=centre.id,
        name="Complete Blood Count",
        description="A standard blood panel.",
        price=550,
        currency="INR",
    )
    db.add(test)
    db.commit()
    return {"admin": admin.id, "user": user.id, "centre": centre.id, "test": test.id}
