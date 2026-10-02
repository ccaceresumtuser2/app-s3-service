import uvicorn

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.api.routes import router

app = FastAPI(
    title="S3 Operations API",
    version="1.0.0",
    description=(
        "API REST para administrar buckets y objetos en Amazon S3. "
        "Las operaciones usan las credenciales AWS del perfil default."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Health", "description": "Estado del servicio."},
        {"name": "Buckets", "description": "Administracion de buckets S3."},
        {"name": "Objects", "description": "Administracion de objetos S3."},
        {"name": "Policies", "description": "Administracion de politicas de bucket."},
    ],
)
app.include_router(router)


def error_response(status_code: int, message: str, code: str, field: str | None = None):
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": message,
            "data": None,
            "errors": [{"code": code, "message": message, "field": field}],
        },
    )


@app.exception_handler(HTTPException)
async def handle_http_error(_, error: HTTPException):
    message = error.detail if isinstance(error.detail, str) else "Solicitud no válida."
    return error_response(error.status_code, message, f"HTTP_{error.status_code}")


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_, error: RequestValidationError):
    errors = [
        {
            "code": item["type"],
            "message": item["msg"],
            "field": ".".join(str(part) for part in item["loc"]),
        }
        for item in error.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Error de validación de la solicitud.",
            "data": None,
            "errors": errors,
        },
    )


@app.exception_handler(ClientError)
async def handle_client_error(_, error: ClientError):
    error_info = error.response.get("Error", {})
    code = error_info.get("Code", "")
    message = error_info.get("Message", "Error al comunicarse con S3")

    if code in {"NoSuchBucket", "NoSuchKey", "NotFound", "404"}:
        status_code = 404
    elif code in {"AccessDenied", "403"}:
        status_code = 403
    elif code in {"BucketAlreadyExists", "BucketAlreadyOwnedByYou", "BucketNotEmpty"}:
        status_code = 409
    elif code in {
        "InvalidBucketName",
        "InvalidArgument",
        "MalformedPolicy",
        "MalformedPolicyDocument",
    }:
        status_code = 400
    else:
        status_code = 502

    return error_response(status_code, message, code or "S3_ERROR")


@app.exception_handler(BotoCoreError)
async def handle_boto_error(_, error: BotoCoreError):
    return error_response(502, str(error), type(error).__name__)


@app.exception_handler(Exception)
async def handle_unexpected_error(_, error: Exception):
    return error_response(500, "Error interno del servidor.", "INTERNAL_SERVER_ERROR")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8090, reload=False)
