import os
import shutil
from pathlib import Path
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["STORAGE_ROOT"] = "/private/tmp/answer-evaluator-test-storage"
os.environ["MAX_UPLOAD_SIZE_BYTES"] = "8"
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import AnswerSheet, Exam, Question, RubricCriterion, Student, User  # noqa: F401
get_settings.cache_clear()
engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
@pytest.fixture(autouse=True)
def database() -> None:
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    shutil.rmtree(Path(os.environ["STORAGE_ROOT"]), ignore_errors=True)
@pytest.fixture
def client() -> TestClient:
    def override_get_db():
        db = TestingSessionLocal()
        try: yield db
        finally: db.close()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client: yield test_client
    app.dependency_overrides.clear()
