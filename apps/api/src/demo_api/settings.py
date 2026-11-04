from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    write_token: str
    s3_enabled: bool
    s3_bucket: str | None


def load_settings() -> Settings:
    s3_enabled = os.getenv("S3_ENABLED", "false").lower() == "true"
    s3_bucket = os.getenv("S3_BUCKET")
    if s3_enabled and not s3_bucket:
        raise ValueError("S3_BUCKET is required when S3_ENABLED=true")
    db_password = os.getenv("DB_PASSWORD")
    write_token = os.getenv("DEMO_WRITE_TOKEN")
    if not db_password or not write_token:
        raise ValueError("DB_PASSWORD and DEMO_WRITE_TOKEN are required")
    return Settings(
        db_host=os.getenv("DB_HOST", "localhost"),
        db_port=int(os.getenv("DB_PORT", "5432")),
        db_name=os.getenv("DB_NAME", "demoapp"),
        db_user=os.getenv("DB_USER", "demoapp"),
        db_password=db_password,
        write_token=write_token,
        s3_enabled=s3_enabled,
        s3_bucket=s3_bucket,
    )
