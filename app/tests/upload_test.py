# app/tests/upload_test.py
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from pathlib import Path
import io
from unittest.mock import AsyncMock, Mock, patch

from app.app import app  # Your FastAPI app
from app.db import get_sync_session
from app.db import User
from app.users import current_active_user




from uuid import uuid4




# Create mock session - DON'T use AsyncMock for add()
mock_session = Mock()  # Use Mock() instead of AsyncMock()
mock_session.added_objects = []
mock_session.committed = False

# Define the add function
def add_side_effect(obj):
    mock_session.added_objects.append(obj)
    print(f"✅ Added to mock session: {obj.caption if hasattr(obj, 'caption') else obj}")

# Set up the mock - use regular Mock for add()
mock_session.add = Mock(side_effect=add_side_effect)

# Use AsyncMock for async methods
async def commit_side_effect():
    mock_session.committed = True
    print("✅ Commit called")

mock_session.commit = AsyncMock(side_effect=commit_side_effect)
mock_session.refresh = AsyncMock()

# Mock execute
async def execute_side_effect(query):
    mock_result = AsyncMock()
    mock_scalars = Mock()
    mock_scalars.first = Mock(return_value=None)
    mock_result.scalars = Mock(return_value=mock_scalars)
    return mock_result

mock_session.execute = AsyncMock(side_effect=execute_side_effect)

@pytest.fixture(autouse=True)
def override_deps():
    async def override_get_db():
        yield mock_session
    
    app.dependency_overrides[get_sync_session] = override_get_db
    
    mock_user = Mock()
    mock_user.id = "123e4567-e89b-12d3-a456-426614174000"
    app.dependency_overrides[current_active_user] = lambda: mock_user
    
    yield
    
    app.dependency_overrides.clear()
    # Reset
    mock_session.added_objects = []
    mock_session.committed = False
    mock_session.add.reset_mock()
    mock_session.commit.reset_mock()


@pytest.fixture
def mock_imagekit():
    with patch('app.app.imagekit.files.upload') as mock:
        mock_result = Mock()
        mock_result.url = "https://ik.imagekit.io/test/image.jpg"
        mock_result.name = "test_image.jpg"
        mock.return_value = mock_result
        yield mock

def test_upload_image(mock_imagekit):
    client = TestClient(app)
    
    test_image = io.BytesIO(b"fake content")
    test_image.seek(0)
    
    files = {"file": ("test.jpg", test_image, "image/jpeg")}
    data = {"caption": "Test caption"}
    
    response = client.post("/upload", files=files, data=data)
    
    print(f"\n=== Test Results ===")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"Mock add called: {mock_session.add.called}")
    print(f"Added objects count: {len(mock_session.added_objects)}")
    
    assert response.status_code == 200
    mock_session.add.assert_called_once()
    assert len(mock_session.added_objects) == 1
    
    added_post = mock_session.added_objects[0]
    assert added_post.caption == "Test caption"
    assert added_post.file_type == "image"





def test_upload_video(mock_imagekit):
    """Test successful video upload"""
    client = TestClient(app)
    
    # Create a test video file
    test_video = io.BytesIO()
    test_video.write(b"fake video content")
    test_video.seek(0)
    
    # Prepare files and form data
    files = {
        "file": ("test_video.mp4", test_video, "video/mp4")
    }
    data = {
        "caption": "Test video caption"
    }
    
    # Make request
    response = client.post("/upload", files=files, data=data)
    
    # Assert response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["file_type"] == "video"
    assert response_data["caption"] == "Test video caption"

def test_upload_missing_file():
    """Test upload without file - should fail"""
    client = TestClient(app)
    
    data = {"caption": "Test caption"}
    response = client.post("/upload", data=data)
    
    assert response.status_code == 422  # Validation error

def test_upload_missing_caption():
    """Test upload without caption - should fail"""
    client = TestClient(app)
    
    test_image = io.BytesIO(b"fake content")
    files = {"file": ("test.jpg", test_image, "image/jpeg")}
    
    response = client.post("/upload", files=files)
    
    assert response.status_code == 422  # Validation error




def test_upload_without_auth():
    async def unauthorized_user():
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    app.dependency_overrides[current_active_user] = unauthorized_user

    client = TestClient(app)

    test_image = io.BytesIO(b"fake content")
    files = {"file": ("test.jpg", test_image, "image/jpeg")}
    data = {"caption": "Test"}

    response = client.post("/upload", files=files, data=data)

    assert response.status_code == 401

    # Restore overrides for other tests
    # pytest.fail("Need to restore overrides")  # Or handle properly



@patch('app.app.imagekit.files.upload')
def test_upload_imagekit_failure(mock_upload):
    mock_upload.return_value = None

    client = TestClient(app, raise_server_exceptions=False)

    test_image = io.BytesIO(b"fake content")
    files = {"file": ("test.jpg", test_image, "image/jpeg")}
    data = {"caption": "Test"}

    response = client.post("/upload", files=files, data=data)

    print(response.status_code)
    print(response.text)

    assert response.status_code == 400



@patch('app.app.imagekit.files.upload')
def test_upload_exception_handling(mock_upload):
    """Test exception handling during upload"""
    # Mock ImageKit to raise an exception
    mock_upload.side_effect = Exception("Network error")
    
    client = TestClient(app)
    
    test_image = io.BytesIO(b"fake content")
    files = {"file": ("test.jpg", test_image, "image/jpeg")}
    data = {"caption": "Test"}
    
    response = client.post("/upload", files=files, data=data)
    
    assert response.status_code == 500
    assert "Network error" in response.json()["detail"]


