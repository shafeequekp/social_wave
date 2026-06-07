import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from fastapi.testclient import TestClient

from app.app import app
from app.db import Post, User
from app.users import current_active_user
from app.tests.database import TestingSessionLocal
from app.dependencies import get_sync_session


from app.db import Base
from app.tests.database import test_engine

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def test_user(async_session):
    user = User(
        email=f"{uuid.uuid4()}@example.com",
        hashed_password="hashed",
        mobile="934083948930"
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user



@pytest_asyncio.fixture
async def async_session():
    async with TestingSessionLocal() as session:
        yield session



@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()




test_base_url = "http://test"

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=test_base_url
    ) as client:
        yield client



@pytest_asyncio.fixture
async def auth_user(async_session, test_user):

    async def override_user():
        return test_user

    async def override_get_session():
        yield async_session

    app.dependency_overrides[current_active_user] = override_user
    app.dependency_overrides[get_sync_session] = override_get_session

    yield test_user


@pytest_asyncio.fixture
async def test_post(async_session, auth_user):
    # Create post
    post = Post(caption="Test Post", 
                user_id=auth_user.id,
                url="some/url/here/",
                file_type="image",
                file_name="some_image.jpeg")
    async_session.add(post)
    await async_session.commit()
    await async_session.refresh(post)
    return post


@pytest.mark.asyncio
async def test_comment_post(client, test_post):

    response = await client.post(
        "/comments",
        params={"text": "sample comment",
                "post_id": str(test_post.id)}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "comment added successfully"

