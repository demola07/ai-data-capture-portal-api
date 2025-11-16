"""
Pytest configuration and fixtures for testing.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Uncomment and configure when ready to add tests
# from app.main import app
# from app.database import Base, get_db

# Test database URL (use in-memory SQLite for tests)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

# @pytest.fixture(scope="session")
# def engine():
#     """Create a test database engine."""
#     engine = create_engine(
#         SQLALCHEMY_DATABASE_URL,
#         connect_args={"check_same_thread": False}
#     )
#     Base.metadata.create_all(bind=engine)
#     yield engine
#     Base.metadata.drop_all(bind=engine)

# @pytest.fixture(scope="function")
# def db_session(engine):
#     """Create a new database session for a test."""
#     TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#     session = TestingSessionLocal()
#     yield session
#     session.rollback()
#     session.close()

# @pytest.fixture(scope="function")
# def client(db_session):
#     """Create a test client with database dependency override."""
#     def override_get_db():
#         try:
#             yield db_session
#         finally:
#             pass
#     
#     app.dependency_overrides[get_db] = override_get_db
#     with TestClient(app) as test_client:
#         yield test_client
#     app.dependency_overrides.clear()
