from fastapi import Depends, status, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Optional

from . import schemas, database, models
from .config import settings
from . import utils

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')

def optional_oauth2_scheme(request: Request):
    # Check if Authorization header is present
    authorization: str = request.headers.get("Authorization")
    
    # If no Authorization header is provided, return None
    if authorization is None:
        return None
    
    # If Authorization header is present, extract the token
    token = authorization.split(" ")[1] if authorization.startswith("Bearer ") else None
    return token

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes


def create_access_token(data: dict):
    to_encode = data.copy()

    # expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def verify_access_token(token: str, credentials_exception):
    try:

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id: str = payload.get("user_id")
        role: str = payload.get("user_role")
        if id is None or role is None:
            raise credentials_exception
        token_data = schemas.TokenData(id=str(id), role=role)
    except JWTError:
        raise credentials_exception

    return token_data


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                          detail=f"Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})

    token = verify_access_token(token, credentials_exception)

    user = db.query(models.User).filter(models.User.id == token.id).first()

    if user is None:
            raise credentials_exception
    
    user.role = utils.Role(user.role)

    return user

# New function: Allow optional authentication
def get_current_user_if_available(
    token: Optional[str] = Depends(optional_oauth2_scheme),
    db: Session = Depends(database.get_db),
):
    try:
         # If token is None, return None (unauthenticated user)
        if token is None:
            return None
        
        # Attempt to verify and fetch the user
        return get_current_user(token, db)
    except HTTPException as e:
        if e.status_code == status.HTTP_401_UNAUTHORIZED:
            # Return None if the credentials are invalid or not provided
            return None
        raise e