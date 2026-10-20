from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from clinic_booking_api.db import engine
from clinic_booking_api.routers import auth, health


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await engine.dispose()


api = APIRouter(prefix="/v1")
api.include_router(health.router)
api.include_router(auth.router)

app = FastAPI(title="Clinic Booking API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST", "PUT"],
)
app.include_router(api)


@app.exception_handler(HTTPException)
async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
    detail = "Not found" if exc.status_code == 404 else exc.detail
    return JSONResponse(status_code=exc.status_code, content={"detail": detail})


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": "Invalid request"})


@app.exception_handler(Exception)
async def unhandled(_request: Request) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
