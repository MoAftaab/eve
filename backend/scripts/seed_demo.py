"""Seed a safe local demo account and catalog; never run this against production."""

from decimal import Decimal

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models import DiagnosticCentre, DiagnosticTest, Role, User
from app.db.session import Base, SessionLocal, engine


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == "admin@example.com")):
            print("Demo data already exists")
            return
        admin = User(email="admin@example.com", full_name="EVE Admin", password_hash=hash_password("AdminPass123"), role=Role.ADMIN)
        patient = User(email="patient@example.com", full_name="Demo Patient", password_hash=hash_password("PatientPass123"))
        centre = DiagnosticCentre(name="Wellness Diagnostics", location="12 Green Avenue")
        db.add_all([admin, patient, centre])
        db.flush()
        db.add_all([
            DiagnosticTest(centre_id=centre.id, name="Complete Blood Count", description="A standard blood panel for a clear baseline.", price=Decimal("550.00"), currency="INR"),
            DiagnosticTest(centre_id=centre.id, name="Lipid Profile", description="A simple check of cholesterol and triglycerides.", price=Decimal("800.00"), currency="INR"),
        ])
        db.commit()
        print("Seeded admin@example.com / AdminPass123 and patient@example.com / PatientPass123")


if __name__ == "__main__":
    main()
