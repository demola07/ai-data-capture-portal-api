from passlib.context import CryptContext
from enum import Enum

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash(password: str):
    return pwd_context.hash(password)


def verify(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "super-admin"