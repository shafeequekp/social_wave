# dependencies.py - CLEAN VERSION
from collections.abc import AsyncGenerator
from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from fastapi_users.db import SQLAlchemyUserDatabase


from app.db import User


# ONLY ONE session dependency with auto-commit
async def get_sync_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    Database session with auto-commit.
    Use this for ALL your endpoints.
    """
    async with request.app.state.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            print(e, 'eeeeeeeeeeeeeeeee')
            await session.rollback()
            raise




# For FastAPI-Users - they need a session without auto-commit
# So create a separate one WITHOUT commit logic
async def get_db_raw(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    Raw session without auto-commit.
    For libraries that manage their own transactions (like FastAPI-Users).
    """
    async with request.app.state.session_factory() as session:
        yield session
        # No commit/rollback - let the library handle it

# FastAPI-Users uses raw session
async def get_user_db(
    session: AsyncSession = Depends(get_db_raw)  # Use raw version
):
    yield SQLAlchemyUserDatabase(session, User)
