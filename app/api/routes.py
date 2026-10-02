from typing import Annotated
from urllib.parse import quote

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.schemas.api_response import ApiResponse
from app.schemas.s3 import (
    AwsConnectionStatus,
    BucketCreate,
    BucketOperation,
    BucketPolicyRequest,
    BucketPolicyOperation,
    BucketSummary,
    DeleteAllObjectsResult,
    ObjectOperation,
    ObjectSummary,
)
from app.services.s3_service import BucketAlreadyExistsError, s3_service

router = APIRouter()


def success_response(data, message: str):
    return {"success": True, "message": message, "data": data, "errors": []}


@router.get("/healthz", tags=["Health"], summary="Comprobar el estado")
def health_check() -> ApiResponse[dict[str, str]]:
    """Indica si el proceso de la API esta respondiendo."""
    return success_response({"status": "ok"}, "Servicio disponible.")


@router.get(
    "/health/aws",
    tags=["Health"],
    summary="Comprobar conexión con AWS",
    response_model=ApiResponse[AwsConnectionStatus],
    responses={503: {"model": ApiResponse[None]}},
)
def check_aws_connection():
    """Valida las credenciales y la conexión con AWS mediante STS."""
    try:
        result = s3_service.check_aws_connection()
        return success_response(result, "Conexión con AWS verificada.")
    except (BotoCoreError, ClientError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get(
    "/buckets",
    tags=["Buckets"],
    summary="Listar buckets",
    response_model=ApiResponse[list[BucketSummary]],
)
def list_buckets():
    """Lista los buckets accesibles con las credenciales configuradas."""
    return success_response(s3_service.list_buckets(), "Buckets listados.")


@router.post(
    "/buckets",
    tags=["Buckets"],
    summary="Crear bucket con fecha",
    status_code=201,
    response_model=ApiResponse[BucketOperation],
    responses={
        409: {
            "model": ApiResponse[None],
            "description": "Ya existe un bucket con el nombre generado.",
        }
    },
)
def create_bucket(payload: BucketCreate):
    """Crea un bucket y agrega la fecha actual en formato DD-MM-YYYY."""
    try:
        result = s3_service.create_bucket(payload.name)
        return success_response(result, "Bucket creado.")
    except BucketAlreadyExistsError as error:
        raise HTTPException(
            status_code=409,
            detail=f"El bucket '{error}' ya existe.",
        ) from error


@router.delete(
    "/buckets/{bucket}",
    tags=["Buckets"],
    summary="Eliminar bucket",
    response_model=ApiResponse[BucketOperation],
)
def delete_bucket(bucket: str):
    """Elimina un bucket vacio."""
    return success_response(s3_service.delete_bucket(bucket), "Bucket eliminado.")


@router.put(
    "/buckets/{bucket}/policy",
    tags=["Policies"],
    summary="Aplicar politica de bucket",
    response_model=ApiResponse[BucketPolicyOperation],
)
def put_bucket_policy(
    bucket: str,
    payload: BucketPolicyRequest,
):
    """Aplica al bucket el documento JSON de la propiedad policies."""
    result = s3_service.put_bucket_policy(bucket.strip(), payload.policies)
    return success_response(result, "Política del bucket aplicada.")


@router.delete(
    "/buckets/{bucket}/policy",
    tags=["Policies"],
    summary="Eliminar politica de bucket",
    response_model=ApiResponse[BucketPolicyOperation],
)
def delete_bucket_policy(bucket: str):
    """Elimina la politica asociada al bucket."""
    result = s3_service.delete_bucket_policy(bucket.strip())
    return success_response(result, "Política del bucket eliminada.")


@router.get(
    "/buckets/{bucket}/objects",
    tags=["Objects"],
    summary="Listar objetos",
    response_model=ApiResponse[list[ObjectSummary]],
)
def list_objects(bucket: str, prefix: str | None = None):
    """Lista los objetos de un bucket, opcionalmente filtrados por prefijo."""
    return success_response(s3_service.list_objects(bucket, prefix), "Objetos listados.")


@router.delete(
    "/buckets/{bucket}/objects",
    tags=["Objects"],
    summary="Eliminar todos los objetos del bucket",
    response_model=ApiResponse[DeleteAllObjectsResult],
    responses={400: {"model": ApiResponse[None], "description": "Se requiere confirm=true."}},
)
def delete_all_objects(bucket: str, confirm: bool = Query(False)):
    """Elimina todos los objetos y sus versiones tras confirmacion explicita."""
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Confirma el borrado irreversible con el parametro confirm=true.",
        )
    result = s3_service.delete_all_objects(bucket.strip())
    return success_response(result, "Operación de borrado masivo completada.")


@router.put(
    "/buckets/{bucket}/objects/{key:path}",
    tags=["Objects"],
    summary="Subir objeto",
    status_code=201,
    response_model=ApiResponse[ObjectOperation],
)
def upload_object(
    bucket: str,
    key: str,
    file: Annotated[UploadFile, File(description="Archivo que se guardara en S3")],
):
    """Sube un archivo; admite keys con segmentos separados por / ."""
    try:
        result = s3_service.upload_object(bucket, key, file.file)
        return success_response(result, "Objeto subido.")
    finally:
        file.file.close()


@router.get(
    "/buckets/{bucket}/objects/{key:path}",
    tags=["Objects"],
    summary="Descargar objeto y guardarlo en C:/download",
    response_class=FileResponse,
    responses={
        200: {
            "description": "Archivo descargado",
            "content": {
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"}
                }
            },
            "headers": {
                "Content-Disposition": {
                    "description": "Nombre de archivo para descarga",
                    "schema": {"type": "string"},
                }
            },
        }
    },
)
def download_object(bucket: str, key: str):
    """Guarda el objeto en C:/download y tambien lo entrega al navegador."""
    result = s3_service.download_object(bucket, key)
    return FileResponse(
        path=result["path"],
        filename=result["filename"],
        media_type=result["content_type"],
        headers={"X-Saved-To": quote(result["path"].as_posix(), safe="/:")},
    )


@router.delete(
    "/buckets/{bucket}/objects/{key:path}",
    tags=["Objects"],
    summary="Eliminar objeto",
    response_model=ApiResponse[ObjectOperation],
)
def delete_object(bucket: str, key: str):
    """Elimina un objeto del bucket indicado."""
    return success_response(s3_service.delete_object(bucket, key), "Objeto eliminado.")