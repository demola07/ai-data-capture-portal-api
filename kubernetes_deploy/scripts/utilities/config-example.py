"""
Configuration for FastAPI app using file-mounted secrets.
All configuration is read from files mounted at /etc/secrets/
"""

import os
from pathlib import Path
from typing import Optional


class Settings:
    """Application settings using file-mounted secrets."""
    
    def __init__(self):
        # All configuration from mounted secret files
        self.database_hostname = self._read_secret_file("database-hostname")
        self.database_port = int(self._read_secret_file("database-port"))
        self.database_name = self._read_secret_file("database-name")
        self.database_username = self._read_secret_file("database-username")
        self.database_password = self._read_secret_file("database-password")
        
        # JWT configuration from files
        self.secret_key = self._read_secret_file("secret-key")
        self.algorithm = self._read_secret_file("algorithm")
        self.access_token_expire_minutes = int(self._read_secret_file("access-token-expire-minutes"))
    
    def _read_secret_file(self, file_name: str) -> str:
        """
        Read secret value from mounted file.
        
        Args:
            file_name: Secret file name in /etc/secrets/
            
        Returns:
            Secret value from file
        """
        file_path = Path(f"/etc/secrets/{file_name}")
        try:
            return file_path.read_text().strip()
        except Exception as e:
            raise ValueError(f"Could not read secret file {file_path}: {e}")
    
    @property
    def database_url(self) -> str:
        """Construct database URL from components."""
        return (
            f"postgresql://{self.database_username}:{self.database_password}"
            f"@{self.database_hostname}:{self.database_port}/{self.database_name}"
        )


# Usage example
settings = Settings()

# In your FastAPI app
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database_connected": bool(settings.database_password),  # Don't expose actual password
        "secrets_loaded": bool(settings.secret_key)
    }


# Alternative: Using Pydantic Settings (recommended)
from pydantic import BaseSettings
from pydantic.fields import Field


class PydanticSettings(BaseSettings):
    """Pydantic-based settings with file secret support."""
    
    # Database configuration
    database_hostname: str = Field(default="localhost", env="DATABASE_HOSTNAME")
    database_port: int = Field(default=5432, env="DATABASE_PORT")
    database_name: str = Field(default="ai_data_capture", env="DATABASE_NAME")
    database_username: str = Field(default="app_user", env="DATABASE_USERNAME")
    
    # JWT configuration
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Load secrets from files after initialization
        self._load_file_secrets()
    
    def _load_file_secrets(self):
        """Load secrets from mounted files."""
        secrets_dir = Path("/etc/secrets")
        
        # Database password
        db_password_file = secrets_dir / "database-password"
        if db_password_file.exists():
            self.database_password = db_password_file.read_text().strip()
        
        # JWT secret key
        secret_key_file = secrets_dir / "secret-key"
        if secret_key_file.exists():
            self.secret_key = secret_key_file.read_text().strip()
    
    @property
    def database_url(self) -> str:
        """Construct database URL."""
        return (
            f"postgresql://{self.database_username}:{self.database_password}"
            f"@{self.database_hostname}:{self.database_port}/{self.database_name}"
        )


# Usage
pydantic_settings = PydanticSettings()
