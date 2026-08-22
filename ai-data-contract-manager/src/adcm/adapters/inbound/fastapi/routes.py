from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()


class CreateSessionRequest(BaseModel):
    user_id: str | None = None


class MessageRequest(BaseModel):
    content: str
    attachments: list[str] = Field(
        default_factory=list,
        description="Inline text contents of attachments. This is not a file path or upload ID.",
        examples=[[]],
    )


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/sessions")
async def create_session(body: CreateSessionRequest, request: Request):
    session = await request.app.state.container.create_session.execute(user_id=body.user_id)
    return {"id": session.id}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, request: Request):
    session = await request.app.state.container.repo.get(session_id)
    if not session:
        raise HTTPException(404, "session not found")
    return session


@router.post("/sessions/{session_id}/messages")
async def message(session_id: str, body: MessageRequest, request: Request):
    try:
        return await request.app.state.container.handle_message.execute(
            session_id, body.content, body.attachments
        )
    except KeyError:
        raise HTTPException(404, "session not found")
