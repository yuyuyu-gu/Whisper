from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from core.config import AppConfig, parse_app_config
from core.context import create_app_context
from modules.utils.logger import get_logger


logger = get_logger()
interview_router = APIRouter(prefix="/interview", tags=["Interview RAG"])


# 初始化应用上下文，获取临时 RAG 聊天服务
_config: AppConfig = parse_app_config([])
_app_context = create_app_context(_config, logger)
_rag_service = _app_context.rag_chat_service


class InterviewFile(BaseModel):
    id: Optional[str] = None
    text: str


class InterviewPayload(BaseModel):
    session_id: Optional[str] = None
    combined_text: Optional[str] = None
    files: Optional[List[InterviewFile]] = None


class CreateSessionRequest(InterviewPayload):
    pass


class CreateSessionResponse(BaseModel):
    success: bool
    session_id: Optional[str]
    chunks_count: int
    message: str


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    payload: Optional[InterviewPayload] = None
    message: str
    history: Optional[List[List[str]]] = None
    model: Optional[str] = "qwen2.5:3b"
    top_k: Optional[int] = 4
    similarity_threshold: Optional[float] = 0.75
    ollama_base_url: Optional[str] = "http://localhost:11434"


class ChatResponse(BaseModel):
    success: bool
    answer: str
    used_context: bool
    session_id: Optional[str]
    context_snippets: List[str]


class SessionInfoResponse(BaseModel):
    exists: bool
    session_id: Optional[str]
    chunks_count: int
    created_at: Optional[float] = None


class BasicResponse(BaseModel):
    success: bool
    message: str


@interview_router.post(
    "/session",
    response_model=CreateSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or update interview session",
)
async def create_or_update_session(payload: CreateSessionRequest) -> CreateSessionResponse:
    data: Dict[str, Any] = payload.model_dump()
    session_id = _rag_service.ensure_session(data)
    if not session_id:
        return CreateSessionResponse(
            success=False,
            session_id=None,
            chunks_count=0,
            message="缺少有效的访谈文本。",
        )

    session = _rag_service._sessions.get(session_id)  # type: ignore[attr-defined]
    chunks = (session or {}).get("chunks") or []
    return CreateSessionResponse(
        success=True,
        session_id=session_id,
        chunks_count=len(chunks),
        message="访谈会话已准备完成。",
    )


@interview_router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question based on interview session",
)
async def chat_with_interview(req: ChatRequest) -> ChatResponse:
    payload_dict: Optional[Dict[str, Any]] = None

    if req.payload:
        payload_dict = req.payload.model_dump()
        if req.session_id and not payload_dict.get("session_id"):
            payload_dict["session_id"] = req.session_id
    elif req.session_id:
        payload_dict = {"session_id": req.session_id}

    if not payload_dict:
        raise HTTPException(status_code=400, detail="会话不存在且未提供有效的访谈文本。")

    answer, used_context = _rag_service.generate_reply(
        payload=payload_dict,
        user_message=req.message,
        history=req.history or [],
        base_url=req.ollama_base_url or "http://localhost:11434",
        model=req.model or "qwen2.5:3b",
        top_k=req.top_k or 4,
        similarity_threshold=req.similarity_threshold or 0.75,
    )

    session_id = payload_dict.get("session_id")
    session = _rag_service._sessions.get(session_id) if session_id else None  # type: ignore[attr-defined]
    context_snippets: List[str] = []
    if session and (session.get("chunks") is not None):
        # 简单返回所有 chunks 作为上下文片段示例；如需更精细可在 service 内暴露检索结果
        context_snippets = list(session.get("chunks") or [])[: (req.top_k or 4)]

    return ChatResponse(
        success=True,
        answer=answer,
        used_context=used_context,
        session_id=session_id,
        context_snippets=context_snippets,
    )


@interview_router.get(
    "/session/{session_id}",
    response_model=SessionInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Get interview session info",
)
async def get_session_info(session_id: str) -> SessionInfoResponse:
    session = _rag_service._sessions.get(session_id)  # type: ignore[attr-defined]
    if not session:
        return SessionInfoResponse(exists=False, session_id=session_id, chunks_count=0, created_at=None)
    chunks = session.get("chunks") or []
    return SessionInfoResponse(
        exists=True,
        session_id=session_id,
        chunks_count=len(chunks),
        created_at=session.get("created_at"),
    )


@interview_router.delete(
    "/session/{session_id}",
    response_model=BasicResponse,
    status_code=status.HTTP_200_OK,
    summary="Clear interview session",
)
async def clear_session(session_id: str) -> BasicResponse:
    _rag_service.clear_session(session_id)
    return BasicResponse(success=True, message=f"会话 {session_id} 已清理。")
