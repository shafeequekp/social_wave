from fastapi.testclient import TestClient
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.app import app
from app.db import Post, User
from app.users import current_active_user
from app.tests.database import TestingSessionLocal
from app.dependencies import get_sync_session


transport = ASGITransport(app=app)

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
        email="test1@example.com",
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




@pytest.mark.asyncio
async def test_add_like_success(async_session, test_user):
    # Create post
    post = Post(caption="Test Post", 
                user_id=test_user.id,
                url="some/url/here/",
                file_type="image",
                file_name="some_image.jpeg")
    async_session.add(post)
    await async_session.commit()
    await async_session.refresh(post)


    # Override current user dependency
    # app.dependency_overrides[current_active_user] = lambda: test_user
    async def override_user():
        return test_user

    async def override_get_session():
        yield async_session

    app.dependency_overrides[current_active_user] = override_user
    app.dependency_overrides[get_sync_session] = override_get_session

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/like",
            params={"post_id": str(post.id)}
        )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert "like_id" in data

    app.dependency_overrides.clear()


