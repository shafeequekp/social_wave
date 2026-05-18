from collections.abc import AsyncGenerator
import uuid
import datetime

from sqlalchemy import  Column, Integer, String, Text, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session, DeclarativeBase, sessionmaker, relationship
from fastapi_users.db import SQLAlchemyUserDatabase, SQLAlchemyBaseUserTableUUID
from fastapi import Depends


class Base(DeclarativeBase):
    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    mobile = Column(String, nullable=True)

    likes = relationship("Like", back_populates="user")
    comments = relationship("Comment", back_populates="user")
    posts = relationship("Post", back_populates="user")


class Post(Base):
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    caption = Column(Text)
    url = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    is_published = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="posts")
    likes = relationship("Like", back_populates="post")
    comments = relationship("Comment", back_populates="post")


class Like(Base):
    __tablename__ = "likes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    # created_at = Column(DateTime, default=datetime.datetime.utcnow)
    liked_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="likes")
    post = relationship("Post", back_populates="likes")

    __table_args__ = (
        UniqueConstraint("user_id", "post_id"),
    )


class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    text = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="comments")
    post = relationship("Post", back_populates="comments")



# DATABASE_URL = "sqlite+aiosqlite:///test.db"
DATABASE_URL = "postgresql+asyncpg://fast_user:1234@db:5432/fast_db"

engine = create_async_engine(DATABASE_URL, future=True, echo=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


# async def create_db_and_tables():
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)

async def get_sync_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_sync_session)):
    yield SQLAlchemyUserDatabase(session, User)
