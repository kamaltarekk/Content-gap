"""Uniform error envelope (spec §11.20). No secrets, stack traces, or raw source text."""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def _envelope(code: str, message: str, details: dict[str, object], request_id: str) -> dict[str, object]:
    return {"error": {"code": code, "message": message, "details": details, "request_id": request_id}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = str(exc.detail) if isinstance(exc.detail, str) else "http_error"
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(code.upper(), code, {}, str(uuid.uuid4())),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = sorted({".".join(str(p) for p in e.get("loc", []) if p != "body") for e in exc.errors()})
        body = _envelope("VALIDATION_ERROR", "Request validation failed.", {"fields": fields}, str(uuid.uuid4()))
        return JSONResponse(status_code=422, content=body)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Never leak stack traces or messages that may contain source text/secrets.
        return JSONResponse(
            status_code=500,
            content=_envelope("INTERNAL_ERROR", "An unexpected error occurred.", {}, str(uuid.uuid4())),
        )
