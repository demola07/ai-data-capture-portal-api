from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import convert, user, auth, counsellor, upload
from . import models
from .database import engine

# models.Base.metadata.create_all(bind=engine)
app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(convert.router)
app.include_router(counsellor.router)
app.include_router(upload.router)

@app.get("/")
def read_root():
    return {"Hello": "World - YMR IS HERE - FLOODGATES!!!!!!!"}