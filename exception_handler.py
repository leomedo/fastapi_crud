from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.requests import Request
from starlette.responses import JSONResponse

from main import app


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"status": "validation_error", "message": str(exc.errors())}
    )