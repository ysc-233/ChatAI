"""Custom exceptions and error response utilities."""
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base application exception."""
    def __init__(self, code: int, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# Error code constants
ERR_BAD_REQUEST = 40000
ERR_CHARACTER_NAME_REQUIRED = 40001
ERR_CHARACTER_BACKGROUND_REQUIRED = 40002
ERR_CHARACTER_PERSONALITY_REQUIRED = 40003
ERR_SESSION_ROLE_CHANGE_WARNING = 40004
ERR_AVATAR_TYPE_UNSUPPORTED = 40005
ERR_AVATAR_SIZE_EXCEEDED = 40006
ERR_AVATAR_INVALID_IMAGE = 40007
ERR_MESSAGE_CONTENT_EMPTY = 40008
ERR_MESSAGE_CONTENT_TOO_LONG = 40009
ERR_UNAUTHORIZED = 40100
ERR_API_KEY_INVALID = 40101
ERR_FORBIDDEN = 40300
ERR_SYSTEM_CHARACTER_IMMUTABLE = 40301
ERR_SYSTEM_CHARACTER_UNDELETABLE = 40302
ERR_DEFAULT_PERSONA_NAME_IMMUTABLE = 40303
ERR_DEFAULT_PERSONA_UNDELETABLE = 40304
ERR_NOT_FOUND = 40400
ERR_CHARACTER_NOT_FOUND = 40401
ERR_PERSONA_NOT_FOUND = 40402
ERR_SESSION_NOT_FOUND = 40403
ERR_MESSAGE_NOT_FOUND = 40404
ERR_STATE_NOT_FOUND = 40405
ERR_PAYLOAD_TOO_LARGE = 41300
ERR_UNPROCESSABLE_ENTITY = 42200
ERR_INTERNAL_ERROR = 50000
ERR_LLM_API_ERROR = 50001
ERR_LLM_API_TIMEOUT = 50002
ERR_EMBEDDING_API_ERROR = 50003
ERR_QDRANT_ERROR = 50004
ERR_REDIS_ERROR = 50005
ERR_DB_ERROR = 50006
ERR_MEMORY_EXTRACT_ERROR = 50007
ERR_STATE_UPDATE_ERROR = 50008


# Predefined exceptions
class CharacterNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail={"code": ERR_CHARACTER_NOT_FOUND, "message": "对话角色不存在"})

class PersonaNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail={"code": ERR_PERSONA_NOT_FOUND, "message": "用户角色不存在"})

class SessionNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail={"code": ERR_SESSION_NOT_FOUND, "message": "会话不存在"})

class MessageNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail={"code": ERR_MESSAGE_NOT_FOUND, "message": "消息不存在"})

class Unauthorized(HTTPException):
    def __init__(self):
        super().__init__(status_code=401, detail={"code": ERR_UNAUTHORIZED, "message": "未认证：缺少有效令牌"})

class Forbidden(HTTPException):
    def __init__(self, message: str = "禁止访问"):
        super().__init__(status_code=403, detail={"code": ERR_FORBIDDEN, "message": message})


async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "data": None}
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": str(detail), "data": None}
    )
