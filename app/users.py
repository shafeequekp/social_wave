import uuid
from fastapi import Depends, HTTPException, Request, status
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy

from app.db import User
from app.dependencies import get_user_db



SECRET = 'ERhsHqmnbopLXZ'

class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f'User {user} has registered')

    async def on_after_forgot_password(self, user: User, request: Optional[Request] = None):
        print(f'User {user} has forgot their password')

    # async def on_after_login(self, user: User, request: Optional[Request] = None):
    #     print(f'User {user} has logged in')

    async def on_after_request_verify(self, user: User, token: str, request: Optional[Request] = None):
        print(f'User {user} has verified. Token {token}')


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)

bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy():
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name='jwt',
    get_strategy=get_jwt_strategy,
    transport=bearer_transport,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, auth_backends=[auth_backend])
current_active_user = fastapi_users.current_user(active=True)


