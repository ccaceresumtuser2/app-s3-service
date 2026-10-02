import json
from typing import Any, BinaryIO

import s3_operations


class S3Repository:
    """Capa de acceso a Amazon S3."""

    def __init__(self):
        self.client = s3_operations.s3
        self.sts_client = s3_operations.session.client("sts")

    def get_aws_identity(self):
        return self.sts_client.get_caller_identity()

    def list_buckets(self):
        response = self.client.list_buckets()
        return [
            {
                "name": bucket["Name"],
                "creation_date": bucket["CreationDate"].isoformat(),
            }
            for bucket in response.get("Buckets", [])
        ]

    def bucket_exists(self, name: str):
        return any(bucket["name"] == name for bucket in self.list_buckets())

    def create_bucket(self, name: str):
        if s3_operations.REGION == "us-east-1":
            self.client.create_bucket(Bucket=name)
        else:
            self.client.create_bucket(
                Bucket=name,
                CreateBucketConfiguration={
                    "LocationConstraint": s3_operations.REGION
                },
            )

    def delete_bucket(self, name: str):
        self.client.delete_bucket(Bucket=name)

    def put_bucket_policy(self, bucket: str, policy: dict[str, Any]):
        self.client.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))

    def delete_bucket_policy(self, bucket: str):
        self.client.delete_bucket_policy(Bucket=bucket)

    def list_objects(self, bucket: str, prefix: str | None = None):
        paginator = self.client.get_paginator("list_objects_v2")
        pages = paginator.paginate(
            Bucket=bucket,
            **({"Prefix": prefix} if prefix else {}),
        )
        return [
            {
                "key": item["Key"],
                "size": item["Size"],
                "last_modified": item["LastModified"].isoformat(),
            }
            for page in pages
            for item in page.get("Contents", [])
        ]

    def upload_object(self, bucket: str, key: str, file: BinaryIO):
        self.client.upload_fileobj(file, bucket, key)

    def get_object(self, bucket: str, key: str):
        return self.client.get_object(Bucket=bucket, Key=key)

    def delete_object(self, bucket: str, key: str):
        self.client.delete_object(Bucket=bucket, Key=key)

    def delete_all_objects(self, bucket: str):
        versioning_status = self.client.get_bucket_versioning(Bucket=bucket).get(
            "Status"
        )
        deleted_count = 0
        errors = []

        if versioning_status in ("Enabled", "Suspended"):
            paginator = self.client.get_paginator("list_object_versions")
            for page in paginator.paginate(Bucket=bucket):
                objects = [
                    {"Key": item["Key"], "VersionId": item["VersionId"]}
                    for item in page.get("Versions", []) + page.get("DeleteMarkers", [])
                ]
                batch_result = self._delete_object_batches(bucket, objects)
                deleted_count += batch_result["deleted_count"]
                errors.extend(batch_result["errors"])
        else:
            paginator = self.client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket):
                objects = [
                    {"Key": item["Key"]}
                    for item in page.get("Contents", [])
                ]
                batch_result = self._delete_object_batches(bucket, objects)
                deleted_count += batch_result["deleted_count"]
                errors.extend(batch_result["errors"])

        return {"deleted_count": deleted_count, "errors": errors}

    def _delete_object_batches(self, bucket: str, objects: list[dict[str, str]]):
        deleted_count = 0
        errors = []
        for offset in range(0, len(objects), 1000):
            response = self.client.delete_objects(
                Bucket=bucket,
                Delete={"Objects": objects[offset : offset + 1000], "Quiet": False},
            )
            deleted_count += len(response.get("Deleted", []))
            errors.extend(response.get("Errors", []))
        return {"deleted_count": deleted_count, "errors": errors}