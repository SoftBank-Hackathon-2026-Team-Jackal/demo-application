"""Optional S3 adapter; disabled for the PostgreSQL migration demo."""

from demo_api.settings import Settings


def put_object(settings: Settings, key: str, body: bytes) -> None:
    if not settings.s3_enabled or not settings.s3_bucket:
        raise RuntimeError("S3 feature is disabled")
    import boto3

    boto3.client("s3").put_object(Bucket=settings.s3_bucket, Key=key, Body=body)
