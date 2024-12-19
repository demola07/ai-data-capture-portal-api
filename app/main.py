from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import convert, user, auth, counsellor, counsellee, upload
from . import models
from .database import engine

# models.Base.metadata.create_all(bind=engine)
app = FastAPI()

# origins = ["*"]
origins = ["https://preview--docu-display-fusion.lovable.app", "http://172.24.70.25:8080", "http://www.ymr-front-end-app.s3-website-us-east-1.amazonaws.com", "https://id-preview--ba8be7b5-3c14-44c5-92fb-b3906387b4ff.lovable.app"]

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
app.include_router(counsellee.router)
app.include_router(upload.router)

@app.get("/")
def read_root():
    return {"Hello": "World - YMR IS HERE - FLOODGATES"}