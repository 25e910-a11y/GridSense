from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.database import Base, get_db
from app.main import app
from app.models.user import User

TEST_DB_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    settings.INGEST_API_KEY = "test-device-ingest-key"
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db):
    user = User(
        username="admin_tester",
        password_hash=hash_password("adminpass123"),
        role="admin",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_headers(admin_user):
    token = create_access_token(admin_user.username, admin_user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def technician_user(db):
    user = User(
        username="tech_tester",
        password_hash=hash_password("techpass123"),
        role="technician",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def technician_headers(technician_user):
    token = create_access_token(technician_user.username, technician_user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def operator_user(db):
    user = User(
        username="operator_tester",
        password_hash=hash_password("operatorpass123"),
        role="operator",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def operator_headers(operator_user):
    token = create_access_token(operator_user.username, operator_user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def shift_incharge_user(db):
    user = User(
        username="shift_tester",
        password_hash=hash_password("shiftpass123"),
        role="shift_incharge",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def shift_incharge_headers(shift_incharge_user):
    token = create_access_token(shift_incharge_user.username, shift_incharge_user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def engineer_user(db):
    user = User(
        username="engineer_tester",
        password_hash=hash_password("engpass123"),
        role="electrical_engineer",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def engineer_headers(engineer_user):
    token = create_access_token(engineer_user.username, engineer_user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def management_user(db):
    user = User(
        username="mgmt_tester",
        password_hash=hash_password("mgmtpass123"),
        role="management",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def management_headers(management_user):
    token = create_access_token(management_user.username, management_user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def ingest_headers():
    return {"X-Ingest-Key": settings.INGEST_API_KEY}
