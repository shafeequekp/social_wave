# settings.py - Updated for Pydantic V2
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ConfigDict
from typing import Optional, Dict, Any
import os
from pathlib import Path

class Settings(BaseSettings):
    # App
    APP_NAME: str = "My FastAPI App"
    DEBUG: bool = Field(default=False, validation_alias="DEBUG")
    ENVIRONMENT: str = Field(default="production", validation_alias="ENVIRONMENT")
    SECRET_KEY: str = Field(default="dev-secret-key-change-in-production", validation_alias="SECRET_KEY")
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://fast_user:1234@db:5432/fast_db",
        validation_alias="DATABASE_URL"
    )
    
    # Pool Settings
    DB_POOL_SIZE: int = Field(default=20, validation_alias="DB_POOL_SIZE", ge=1, le=100)
    DB_MAX_OVERFLOW: int = Field(default=40, validation_alias="DB_MAX_OVERFLOW", ge=0)
    DB_POOL_TIMEOUT: int = Field(default=30, validation_alias="DB_POOL_TIMEOUT")
    DB_POOL_RECYCLE: int = Field(default=3600, validation_alias="DB_POOL_RECYCLE")
    DB_POOL_PRE_PING: bool = Field(default=True, validation_alias="DB_POOL_PRE_PING")
    DB_ECHO: bool = Field(default=False, validation_alias="DB_ECHO")
    
    # ImageKit - Made Optional with None default
    IMAGEKIT_PRIVATE_KEY: Optional[str] = Field(default=None, validation_alias="IMAGEKIT_PRIVATE_KEY")
    IMAGEKIT_PUBLIC_KEY: Optional[str] = Field(default=None, validation_alias="IMAGEKIT_PUBLIC_KEY")
    IMAGEKIT_URL: Optional[str] = Field(default=None, validation_alias="IMAGEKIT_URL")
    
    # Groq API - Made Optional with None default
    GROQ_API_KEY: Optional[str] = Field(default=None, validation_alias="GROQ_API_KEY")

    # HOST
    HOST: str = Field(default="http://13.201.75.191")  # Production default

    
    # ✅ Pydantic V2: Use model_config instead of class Config
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Ignore extra fields from local.py
    )

    
    # ✅ Pydantic V2: Use field_validator instead of validator
    @field_validator("DB_POOL_SIZE")
    @classmethod
    def validate_pool_size(cls, v: int, info) -> int:
        """Ensure pool size is reasonable"""
        # In Pydantic V2, access other values via info.data
        if info.data.get("DEBUG") and v > 10:
            print(f"Warning: Large pool size {v} in DEBUG mode")
        return v
    
    def get_db_settings(self) -> Dict[str, Any]:
        """Get database connection settings as dict"""
        return {
            "pool_size": self.DB_POOL_SIZE,
            "max_overflow": self.DB_MAX_OVERFLOW,
            "pool_timeout": self.DB_POOL_TIMEOUT,
            "pool_recycle": self.DB_POOL_RECYCLE,
            "pool_pre_ping": self.DB_POOL_PRE_PING,
            "echo": self.DB_ECHO,
        }

# Create settings instance
settings = Settings()

# Debug output (commented out by default)
# print(f"🔧 Settings loaded:")
# print(f"   ENVIRONMENT: {settings.ENVIRONMENT}")
# print(f"   DEBUG: {settings.DEBUG}")
# print(f"   DATABASE_URL: {settings.DATABASE_URL[:50]}...")



# Manually load and apply local.py if it exists
try:
    from .local import *  # Import local overrides
    # Update settings with local values
    for key, value in locals().items():
        if key.isupper() and hasattr(settings, key):
            setattr(settings, key, value)
    print("✅ Loaded local.py overrides")
except ImportError:
    print("ℹ️ local.py not found, using base settings")


