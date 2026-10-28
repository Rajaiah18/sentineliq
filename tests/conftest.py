"""
SentinelIQ Pytest Test Configuration & Fixtures
Isolated test database/memory store, HTTP test client, and authenticated session headers.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.config import settings
from backend.app.main import app
from backend.app.database.repository import repo
from backend.app.security.auth import create_access_token


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Ensure tests run in memory mode without touching external databases."""
    settings.APP_STORAGE = "memory"
    settings.APP_ENV = "test"
    repo.storage_mode = "memory"


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def admin_token():
    """JWT Bearer token for ADMIN role."""
    return create_access_token({"sub": "admin", "role": "ADMIN"})


@pytest.fixture
def analyst_token():
    """JWT Bearer token for ANALYST role."""
    return create_access_token({"sub": "analyst", "role": "ANALYST"})


@pytest.fixture
def compliance_token():
    """JWT Bearer token for COMPLIANCE_REVIEWER role."""
    return create_access_token({"sub": "compliance", "role": "COMPLIANCE_REVIEWER"})


@pytest.fixture
def readonly_token():
    """JWT Bearer token for READ_ONLY role."""
    return create_access_token({"sub": "readonly", "role": "READ_ONLY"})


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def analyst_headers(analyst_token):
    return {"Authorization": f"Bearer {analyst_token}"}


@pytest.fixture
def compliance_headers(compliance_token):
    return {"Authorization": f"Bearer {compliance_token}"}


@pytest.fixture
def readonly_headers(readonly_token):
    return {"Authorization": f"Bearer {readonly_token}"}
