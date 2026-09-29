from fastapi import HTTPException


def fail(status: int, code: str, message: str, **details):
    raise HTTPException(status, {"code": code, "message": message, "details": details})
