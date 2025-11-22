import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from app.main import app
from app.services.ai_extraction import AIProvider

client = TestClient(app)

# Mock data matching Convert schema
MOCK_EXTRACTED_DATA = {
    "name": "John Doe",
    "gender": "Male",
    "email": "john@example.com",
    "phone_number": "1234567890",
    "date_of_birth": "1990-01-01",
    "relationship_status": "Single",
    "country": "Nigeria",
    "state": "Lagos",
    "address": "123 Main St",
    "nearest_bus_stop": "Central Station",
    "is_student": False,
    "age_group": "Adult",
    "school": "N/A",
    "occupation": "Engineer",
    "denomination": "Orthodox",
    "availability_for_follow_up": True,
    "online": False
}

@pytest.fixture
def mock_ai_provider():
    with patch("app.services.ai_extraction.get_ai_provider") as mock_get:
        mock_provider = AsyncMock(spec=AIProvider)
        mock_provider.extract_data.return_value = MOCK_EXTRACTED_DATA
        mock_get.return_value = mock_provider
        yield mock_provider

from app import oauth2

@pytest.fixture
def mock_auth():
    # Bypass authentication for testing using dependency overrides
    mock_user = MagicMock(role="admin")
    app.dependency_overrides[oauth2.get_current_user] = lambda: mock_user
    yield mock_user
    app.dependency_overrides = {}


def test_extract_endpoint_success(mock_ai_provider, mock_auth):
    # Create a dummy image file
    files = [
        ("files", ("test.jpg", b"fake_image_content", "image/jpeg"))
    ]
    
    response = client.post("/api/capture/extract", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["name"] == "John Doe"
    assert data[0]["email"] == "john@example.com"

def test_extract_endpoint_invalid_file_type(mock_auth):
    files = [
        ("files", ("test.txt", b"text content", "text/plain"))
    ]
    
    response = client.post("/api/capture/extract", files=files)
    
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]

def test_extract_endpoint_no_files(mock_auth):
    response = client.post("/api/capture/extract", files=[])
    # FastAPI might return 422 for missing required field, or we handle it.
    # Our code raises 400 if !files, but FastAPI validation might catch it first as 422.
    # Let's check for either.
    assert response.status_code in [400, 422]
