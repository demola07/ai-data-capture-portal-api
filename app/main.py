from fastapi import FastAPI
from .routers import convert, user, auth, counsellor
from . import models
from .database import engine

models.Base.metadata.create_all(bind=engine)
app = FastAPI()

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(convert.router)
app.include_router(counsellor.router)

@app.get("/")
def read_root():
    return {"Hello": "World"}