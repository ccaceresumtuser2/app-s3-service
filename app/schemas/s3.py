from typing import Any

from pydantic import BaseModel, Field


class BucketCreate(BaseModel):
    name: str = Field(
        min_length=3,
        max_length=52,
        description="Nombre base; la API agrega la fecha en formato DD-MM-YYYY.",
    )


class BucketSummary(BaseModel):
    name: str
    creation_date: str


class BucketOperation(BaseModel):
    name: str
    created: bool | None = None
    deleted: bool | None = None


class BucketPolicyOperation(BaseModel):
    bucket: str
    applied: bool | None = None
    deleted: bool | None = None


class BucketPolicyRequest(BaseModel):
    policies: dict[str, Any] = Field(
        description="Documento JSON de la politica que se aplicara al bucket."
    )


class AwsConnectionStatus(BaseModel):
    connected: bool
    account_id: str | None = None
    arn: str | None = None
    region: str | None = None
    message: str | None = None


class ObjectSummary(BaseModel):
    key: str
    size: int
    last_modified: str


class ObjectOperation(BaseModel):
    bucket: str
    key: str
    uploaded: bool | None = None
    deleted: bool | None = None


class DeleteAllObjectsResult(BaseModel):
    bucket: str
    deleted_count: int
    errors: list[dict[str, Any]]