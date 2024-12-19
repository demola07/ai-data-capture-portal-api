# from sqlalchemy import create_engine
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker
# import psycopg2
# from psycopg2.extras import RealDictCursor
# import time
# from .config import settings

# SQLALCHEMY_DATABASE_URL = f'postgresql://{settings.database_username}:{settings.database_password}@{settings.database_hostname}:{settings.database_port}/{settings.database_name}'


# engine = create_engine(SQLALCHEMY_DATABASE_URL)

# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base = declarative_base()


# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from tenacity import retry, wait_fixed, stop_after_attempt
from sqlalchemy.exc import OperationalError
import time
from .config import settings

SQLALCHEMY_DATABASE_URL = f'postgresql://{settings.database_username}:{settings.database_password}@{settings.database_hostname}:{settings.database_port}/{settings.database_name}'

@retry(wait=wait_fixed(2), stop=stop_after_attempt(5), reraise=True)
def get_engine_with_retry():
    return create_engine(
        SQLALCHEMY_DATABASE_URL,
        poolclass=QueuePool,
        pool_size=10,         # Number of connections in the pool
        max_overflow=20,      # Additional connections beyond pool_size
        pool_timeout=30,      # Timeout for getting a connection from the pool
        pool_recycle=1800,    # Recycle connections after a certain time (in seconds)
)

engine = get_engine_with_retry()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    retries = 3
    delay = 5  # seconds

    for attempt in range(retries):
        try:
            db = SessionLocal()
            yield db
            break
        except OperationalError as e:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise e
        finally:
            if 'db' in locals():
                db.close()
