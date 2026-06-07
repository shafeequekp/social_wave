# app/tests/upload_test.py

import io
import pytest
import pytest_asyncio

from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, Mock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.app import app
from app.db import User
from app.dependencies import get_sync_session
from app.users import current_active_user


# ----------------------------
# Client Fixture
# ----------------------------

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


# ----------------------------
# Mock Session Fixture
# ----------------------------

@pytest.fixture
def mock_session():
    session = Mock()

    session.added_objects = []
    session.committed = False

    def add_side_effect(obj):
        session.added_objects.append(obj)

    session.add = Mock(side_effect=add_side_effect)

    async def commit_side_effect():
        session.committed = True

    session.commit = AsyncMock(side_effect=commit_side_effect)
    session.refresh = AsyncMock()

    async def execute_side_effect(query):
        result = AsyncMock()
        scalars = Mock()
        scalars.first = Mock(return_value=None)
        result.scalars = Mock(return_value=scalars)
        return result

    session.execute = AsyncMock(side_effect=execute_side_effect)

    return session


# ----------------------------
# Dependency Override Fixture
# ----------------------------

@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


# @pytest.fixture
# def mock_session():
#     session = Mock()

#     session.added_objects = []

#     def add_side_effect(obj):
#         session.added_objects.append(obj)

#     session.add = Mock(side_effect=add_side_effect)
#     session.commit = AsyncMock()
#     session.refresh = AsyncMock()
#     session.execute = AsyncMock()

#     return session


@pytest.fixture(autouse=True)
def override_deps(mock_session):

    async def override_get_db():
        yield mock_session

    mock_user = Mock(spec=User)
    mock_user.id = "123e4567-e89b-12d3-a456-426614174000"

    app.dependency_overrides[get_sync_session] = override_get_db
    app.dependency_overrides[current_active_user] = lambda: mock_user

    yield

# ----------------------------
# Upload Fixtures
# ----------------------------

@pytest.fixture
def image_file():
    return (
        "test.jpg",
        io.BytesIO(b"fake image content"),
        "image/jpeg"
    )


@pytest.fixture
def video_file():
    return (
        "test.mp4",
        io.BytesIO(b"fake video content"),
        "video/mp4"
    )

# ----------------------------
# ImageKit Fixture
# ----------------------------

@pytest.fixture
def mock_imagekit():
    with patch("app.app.imagekit.files.upload") as mock:
        result = Mock()
        result.url = "https://ik.imagekit.io/test/image.jpg"
        result.name = "test_image.jpg"

        mock.return_value = result

        yield mock


# ----------------------------
# Tests
# ----------------------------

@pytest.mark.asyncio
async def test_upload_image(
    client,
    mock_session,
    mock_imagekit,
    image_file
):
    response = await client.post(
        "/upload",
        files={"file": image_file},
        data={"caption": "Test caption"}
    )

    assert response.status_code == 200

    mock_session.add.assert_called_once()

    added_post = mock_session.added_objects[0]

    assert added_post.caption == "Test caption"
    assert added_post.file_type == "image"


@pytest.mark.asyncio
async def test_upload_video(
    client,
    mock_imagekit,
    video_file
):
    response = await client.post(
        "/upload",
        files={"file": video_file},
        data={"caption": "Video caption"}
    )

    assert response.status_code == 200

    data = response.json()

    assert data["file_type"] == "video"
    assert data["caption"] == "Video caption"


@pytest.mark.asyncio
async def test_upload_missing_file(client):

    response = await client.post(
        "/upload",
        data={"caption": "Test"}
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_missing_caption(
    client,
    image_file
):
    response = await client.post(
        "/upload",
        files={"file": image_file}
    )

    assert response.status_code == 422



@pytest.mark.asyncio
async def test_upload_without_auth(
    client,
    image_file
):
    async def unauthorized_user():
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    app.dependency_overrides[current_active_user] = unauthorized_user

    response = await client.post(
        "/upload",
        files={"file": image_file},
        data={"caption": "Test"}
    )

    assert response.status_code == 401

@pytest.mark.asyncio
async def test_upload_imagekit_failure(
    client,
    image_file
):
    with patch("app.app.imagekit.files.upload") as mock_upload:
        mock_upload.return_value = None

        response = await client.post(
            "/upload",
            files={"file": image_file},
            data={"caption": "Test"}
        )

        assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_exception_handling(
    client,
    image_file
):
    with patch("app.app.imagekit.files.upload") as mock_upload:
        mock_upload.side_effect = Exception("Network error")

        response = await client.post(
            "/upload",
            files={"file": image_file},
            data={"caption": "Test"}
        )

        assert response.status_code == 500

        data = response.json()

        assert data["detail"] == "Network error"

        

