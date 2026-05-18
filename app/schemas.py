from pydantic import BaseModel
from fastapi_users import schemas

from uuid import UUID
from datetime import datetime


class UserRead(schemas.BaseUser[UUID]):
    pass

class UserCreate(schemas.BaseUserCreate):
    pass

class UserUpdate(schemas.BaseUserUpdate):
    pass



class PostCreate(BaseModel):
    title: str
    content: str






class CommentSchema(BaseModel):
    id: int
    text: str
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class FeedPostSchema(BaseModel):
    id: UUID
    user_id: UUID
    caption: str | None
    url: str
    file_type: str
    file_name: str
    created_at: datetime
    is_owner: bool
    email: str | None
    likes: int
    comments: list[CommentSchema]
    is_liked: bool

    class Config:
        from_attributes = True


class FeedResponseSchema(BaseModel):
    posts: list[FeedPostSchema]
