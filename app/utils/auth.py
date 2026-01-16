"""
Authentication and password utilities
"""
from passlib.context import CryptContext
from enum import Enum

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash(password: str):
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify(plain_password, hashed_password):
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


class Role(str, Enum):
    """User role enumeration"""
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "super-admin"
