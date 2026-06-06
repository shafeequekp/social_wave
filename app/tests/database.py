# tests/database.py

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(TEST_DATABASE_URL)

TestingSessionLocal = async_sessionmaker(
    test_engine,
    expire_on_commit=False,
)
