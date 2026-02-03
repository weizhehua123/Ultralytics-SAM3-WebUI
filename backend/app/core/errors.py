from __future__ import annotations

from fastapi import HTTPException


def http_400(message: str) -> HTTPException:
    return HTTPException(status_code=400, detail=message)


def http_404(message: str) -> HTTPException:
    return HTTPException(status_code=404, detail=message)


def http_409(message: str) -> HTTPException:
    return HTTPException(status_code=409, detail=message)


def http_500(message: str) -> HTTPException:
    return HTTPException(status_code=500, detail=message)
