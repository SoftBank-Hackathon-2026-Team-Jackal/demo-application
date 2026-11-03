from contextlib import asynccontextmanager
from datetime import datetime
import hmac
from uuid import UUID, uuid4

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from demo_api.db import connection, ensure_schema
from demo_api.settings import Settings, load_settings


class MessageCreate(BaseModel):
    request_id: UUID
    body: str = Field(min_length=1, max_length=200)

    @field_validator("body")
    @classmethod
    def nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message body cannot be blank")
        return value


class Message(BaseModel):
    id: UUID
    request_id: UUID
    body: str
    created_at: datetime


class MessageList(BaseModel):
    items: list[Message]
    total: int


def create_app(settings: Settings | None = None, initialize: bool = True) -> FastAPI:
    config = settings or load_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if initialize:
            ensure_schema(config)
        yield

    app = FastAPI(title="Migration Demo Message Feed", lifespan=lifespan)

    @app.get("/health")
    def health() -> dict[str, str]:
        try:
            with connection(config) as conn:
                conn.execute("SELECT 1")
        except Exception:
            raise HTTPException(status_code=503, detail="database unavailable") from None
        return {"status": "ok"}

    @app.get("/api/messages", response_model=MessageList)
    def list_messages(limit: int = Query(default=50, ge=1, le=1000)) -> MessageList:
        with connection(config) as conn:
            items = conn.execute(
                "SELECT id, request_id, body, created_at FROM messages "
                "ORDER BY created_at DESC, id DESC LIMIT %s",
                (limit,),
            ).fetchall()
            total = conn.execute("SELECT count(*) AS total FROM messages").fetchone()["total"]
        return MessageList(items=items, total=total)

    @app.get("/api/messages/{message_id}", response_model=Message)
    def get_message(message_id: UUID) -> Message:
        with connection(config) as conn:
            row = conn.execute(
                "SELECT id, request_id, body, created_at FROM messages WHERE id = %s",
                (message_id,),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="message not found")
        return Message(**row)

    @app.post("/api/messages", response_model=Message, status_code=201)
    def post_message(
        payload: MessageCreate,
        x_demo_write_token: str | None = Header(default=None),
    ) -> Message:
        if not x_demo_write_token or not hmac.compare_digest(
            x_demo_write_token, config.write_token
        ):
            raise HTTPException(status_code=401, detail="invalid write token")
        with connection(config) as conn:
            row = conn.execute(
                "INSERT INTO messages (id, request_id, body) VALUES (%s, %s, %s) "
                "ON CONFLICT (request_id) DO NOTHING "
                "RETURNING id, request_id, body, created_at",
                (uuid4(), payload.request_id, payload.body),
            ).fetchone()
            if row is None:
                row = conn.execute(
                    "SELECT id, request_id, body, created_at FROM messages "
                    "WHERE request_id = %s",
                    (payload.request_id,),
                ).fetchone()
                if row["body"] != payload.body:
                    raise HTTPException(status_code=409, detail="request_id already has another body")
        return Message(**row)

    return app


app = create_app()
