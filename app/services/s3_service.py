from datetime import date
from pathlib import Path, PurePosixPath
import re
from typing import Any, BinaryIO

from app.repositories.s3_repository import S3Repository


class BucketAlreadyExistsError(Exception):
    """El nombre final del bucket ya esta ocupado en la cuenta AWS."""


DOWNLOAD_DIRECTORY = Path("C:/download")
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


def safe_path_component(value: str):
    component = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).rstrip(" .")
    if component.upper().split(".")[0] in WINDOWS_RESERVED_NAMES:
        component = f"_{component}"
    return component or "_"


class S3Service:
    """Casos de uso para administrar buckets y objetos S3."""

    def __init__(self, repository: S3Repository):
        self.repository = repository

    def list_buckets(self):
        return self.repository.list_buckets()

    def check_aws_connection(self):
        identity = self.repository.get_aws_identity()
        return {
            "connected": True,
            "account_id": identity.get("Account"),
            "arn": identity.get("Arn"),
            "region": self.repository.client.meta.region_name,
        }

    def create_bucket(self, name: str):
        bucket_date = date.today().strftime("%d-%m-%Y")
        bucket_name = f"{name}-{bucket_date}"
        if self.repository.bucket_exists(bucket_name):
            raise BucketAlreadyExistsError(bucket_name)
        self.repository.create_bucket(bucket_name)
        return {"name": bucket_name, "created": True}

    def delete_bucket(self, name: str):
        self.repository.delete_bucket(name)
        return {"name": name, "deleted": True}

    def put_bucket_policy(self, bucket: str, policy: dict[str, Any]):
        self.repository.put_bucket_policy(bucket, policy)
        return {"bucket": bucket, "applied": True}

    def delete_bucket_policy(self, bucket: str):
        self.repository.delete_bucket_policy(bucket)
        return {"bucket": bucket, "deleted": True}

    def list_objects(self, bucket: str, prefix: str | None):
        return self.repository.list_objects(bucket, prefix)

    def upload_object(self, bucket: str, key: str, file: BinaryIO):
        self.repository.upload_object(bucket, key, file)
        return {"bucket": bucket, "key": key, "uploaded": True}

    def get_object(self, bucket: str, key: str):
        return self.repository.get_object(bucket, key)

    def download_object(self, bucket: str, key: str):
        result = self.repository.get_object(bucket, key)
        key_parts = [
            part
            for part in PurePosixPath(key.replace("\\", "/")).parts
            if part not in {"/", ".", ".."}
        ]
        safe_bucket = safe_path_component(bucket)
        safe_parts = [safe_path_component(part) for part in key_parts] or ["download"]
        destination = DOWNLOAD_DIRECTORY / safe_bucket / Path(*safe_parts)
        destination.parent.mkdir(parents=True, exist_ok=True)

        body = result["Body"]
        try:
            with destination.open("wb") as output_file:
                while chunk := body.read(1024 * 1024):
                    output_file.write(chunk)
        finally:
            body.close()

        return {
            "path": destination,
            "filename": destination.name,
            "content_type": result.get("ContentType", "application/octet-stream"),
        }

    def delete_object(self, bucket: str, key: str):
        self.repository.delete_object(bucket, key)
        return {"bucket": bucket, "key": key, "deleted": True}

    def delete_all_objects(self, bucket: str):
        result = self.repository.delete_all_objects(bucket)
        return {"bucket": bucket, **result}


s3_service = S3Service(S3Repository())