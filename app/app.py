from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, joinedload

from contextlib import asynccontextmanager
# from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
from typing import Optional

import shutil
import os
import uuid
import tempfile
import time

from app.schemas import PostCreate
from app.db import Post, User, Comment, Like, ChatHistory
from app.dependencies import get_sync_session
from app.images import imagekit
from app.users import auth_backend, current_active_user, fastapi_users
from app.schemas import UserCreate, UserRead, UserUpdate, FeedResponseSchema, FeedPostSchema, ChatRequest, ChatHistoryListResponse
from app.middlewares import LoggingMiddleware
from app.services.ai_services import ask_ai
from app.config.settings import settings




@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create engine with pool settings from Settings
    engine = create_async_engine(
        settings.DATABASE_URL,
        **settings.get_db_settings()  # Unpack all pool settings
    )
    
    app.state.engine = engine
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    
    print(f"Running in {settings.ENVIRONMENT} mode")
    print(f"DB Pool size: {settings.DB_POOL_SIZE}")
    
    yield
    
    await engine.dispose()
    print("Database connections closed")

app = FastAPI(lifespan=lifespan)



# app.add_middleware(LoggingMiddleware)






app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"])
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"])










@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    caption: str = Form(...),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_sync_session),
):
    temp_file_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=os.path.splitext(file.filename)[1]
        ) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)
        
        if imagekit is None:
            raise HTTPException(
                status_code=500,
                detail="ImageKit is not configured"
            )

        with open(temp_file_path, "rb") as f:
            upload_result = imagekit.files.upload(
                file=f,
                file_name=file.filename,
                folder="feeds/",
                tags=["backend-uploads"]
            )

        if upload_result is None:
            raise HTTPException(
                status_code=400,
                detail="Upload failed"
            )

        if upload_result.url:
            post = Post(
                user_id=user.id,
                caption=caption,
                url=upload_result.url,
                file_type="video"
                if file.content_type.startswith("video/")
                else "image",
                file_name=upload_result.name,
            )

            session.add(post)

            # await session.commit()
            # await session.refresh(post)

            return post

        raise HTTPException(
            status_code=400,
            detail="Upload failed"
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

        file.file.close()


@app.patch("/posts/{post_id}")
async def update_post(
    post_id: uuid.UUID,
    caption: str = Form(...),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_sync_session),
):
    result = await session.execute(
        select(Post).where(
            Post.id == post_id,
            Post.user_id == user.id
        )
    )

    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    post.caption = caption

    # await session.commit()
    # await session.refresh(post)

    return post



@app.get("/feed", response_model=FeedResponseSchema)
async def get_feeds(session: AsyncSession = Depends(get_sync_session), 
                    user: User = Depends(current_active_user)):
    
    result = await session.execute(select(Post).options(
        selectinload(Post.comments),
        selectinload(Post.likes),
        selectinload(Post.user)
    ).order_by(Post.created_at.desc()))
    posts = result.scalars().all()

    result = await session.execute(select(User))
    users = result.scalars().all()
    user_dict = {u.id: u.email for u in users}

    post_data = []
    for post in posts:
        
        like_count = len(post.likes)

        is_liked = any(like.user_id == user.id for like in post.likes)

        post_data.append(
            FeedPostSchema(
                id=post.id,
                user_id=user.id,
                caption=post.caption,
                url=post.url,
                file_type=post.file_type,
                file_name=post.file_name,
                created_at=post.created_at,
                is_owner=post.user_id == user.id,
                email=user_dict.get(post.user_id),
                likes=like_count,
                comments=post.comments,
                is_liked=is_liked
            )
        )
    return {"posts": post_data}



@app.delete("/posts/{post_id}")
async def delete_post(
        post_id: str, session: AsyncSession = Depends(get_sync_session),
        user: User = Depends(current_active_user)
):
    try:
        post_id = uuid.UUID(post_id)
        print(post_id)

        result = await session.execute(select(Post).where(Post.id == post_id, Post.user_id == user.id))
        post_obj = result.scalars().first()

        if not post_obj:
            raise HTTPException(status_code=404, detail="Post not found")

        await session.delete(post_obj)
        # await session.commit()
        return {"success": True, "message": "Deleted successfully"}
    except ValueError:  # Invalid UUID
        raise HTTPException(status_code=400, detail="Invalid post ID format")
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/comments")
async def create_comment(text: str,
                         post_id: str,
                         user: User = Depends(current_active_user),
                         session: AsyncSession = Depends(get_sync_session)):
    result = await session.execute(select(Post).where(Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=400, detail="Post not found")

    comment = Comment(text=text, post_id=post_id, user_id=user.id)
    session.add(comment)
    # await session.commit()
    return {"success": True, "message": "comment added successfully"}


@app.get("/comments/{post_id}")
async def get_comment(post_id: str, session: AsyncSession = Depends(get_sync_session), user: User = Depends(current_active_user)):
    try:
        result = await session.execute(select(Post).where(Post.id == post_id))
        post = result.scalars().first()
        if not post:
            raise HTTPException(status_code=400, detail="Post not found")

        comment_result = await session.execute(select(Comment).where(Comment.post_id == post_id))
        comments = comment_result.scalars().all()
        return {"comments": comments}
    except Exception:
        raise HTTPException(status_code=404, detail="Post not found")


@app.get("/likes/{post_id}")
async def get_likes(
    post_id: str,
    session: AsyncSession = Depends(get_sync_session),
    user: User = Depends(current_active_user)
):
    result = await session.execute(
        select(Post).where(Post.id == post_id)
    )
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    likes_result = await session.execute(select(func.count(Like.id)).where(Like.post_id == post_id))
    likes_count = likes_result.scalar()
    return {
        "likes_count": likes_count
    }


@app.post("/like")
async def add_like(
    post_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_sync_session)
):
    result = await session.execute(
        select(Post).where(Post.id == post_id)
    )

    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    already_liked = await session.execute(
        select(Like).where(
            Like.post_id == post_id,
            Like.user_id == user.id
        )
    )

    if already_liked.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="User already liked this post"
        )

    like = Like(
        user_id=user.id,
        post_id=post.id
    )

    session.add(like)
    # await session.commit()
    # await session.refresh(like)

    return {
        "success": True,
        "like_id": like.id
    }


@app.post("/unlike")
async def remove_like(
    post_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_sync_session),
):

    result = await session.execute(select(Post).where(Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    already_liked = await session.execute(
        select(Like).where(
            Like.post_id == post_id,
            Like.user_id == user.id
        )
    )
    like = already_liked.scalars().first()
    if not like:
        raise HTTPException(
            status_code=400,
            detail="User has not liked this post"
        )

    await session.delete(like)
    # await session.commit()

    return {
        "success": True,
        "message": "Like removed successfully"
    }



from app.dependencies import get_db_raw

@app.post("/chat")
async def chat(request: ChatRequest, 
               user: User = Depends(current_active_user),
               session: AsyncSession = Depends(get_db_raw)):
    response = ask_ai(request.message)

    history = ChatHistory(question=request.message, answer=response, user_id=user.id)
    session.add(history)
    await session.commit()
    await session.refresh(history)

    return {
        "response": response
    }




@app.get("/chat-history", response_model=ChatHistoryListResponse)
async def chat_history(user: User = Depends(current_active_user), 
                       session: AsyncSession = Depends(get_sync_session)
                       ):
    
    result = await session.execute(select(
        ChatHistory).where(
            ChatHistory.user_id == user.id).order_by(
                ChatHistory.created_at.desc()))

    histories = result.scalars().all()

    return {'histories': histories, 'status': 200}

