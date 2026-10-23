"""
Shared pytest configuration for all backend tests.
Provides a single test DB engine and dependency override,
ensuring all test files use the same database with tables created once.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.main import app
from backend.app.database.session import Base, get_db

TEST_DB_URL = "sqlite:///./test_inside.db"

test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override once at module import level — all test files share this
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    """Create all tables once per test session with clean initial state."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
