import json
import random
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Depends
from api_app.routers import users, files
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.exceptions import HTTPException


app = FastAPI(
    title="Xendpal api",
    summary="This is the api for Xendpal.com ",
    description="Xendpal - An online file sharing platform -",
    version="latest",
)


app.mount("/Uploads", StaticFiles(directory="Uploads"), name="Uploads")

origins = ["*"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def Xendpal():
    return RedirectResponse(url="/redoc", status_code=302)


app.include_router(users.router)
app.include_router(files.router)
