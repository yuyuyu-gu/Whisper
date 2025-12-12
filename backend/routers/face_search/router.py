from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from core.config import AppConfig, parse_app_config
from core.context import create_app_context
from modules.face_search.service import FaceSearchService
from modules.utils.logger import get_logger


logger = get_logger()
face_search_router = APIRouter(prefix="/face-search", tags=["Face Search"])


# 初始化 FaceSearchService，与 AppContext 中保持路径一致
_config: AppConfig = parse_app_config([])
_app_context = create_app_context(_config, logger)
_face_service: FaceSearchService = _app_context.face_search_service


class IndexResponse(BaseModel):
    success: bool
    processed_images: int
    total_faces: int
    errors: List[str] = []
    message: str


class SearchMatch(BaseModel):
    image_path: str
    distance: float
    original_path: Optional[str] = None


class SearchResponse(BaseModel):
    success: bool
    matches: List[SearchMatch]


class StatsResponse(BaseModel):
    total_faces: int
    total_images: int
    total_indexed_files: int


class ResetRequest(BaseModel):
    confirm: bool = False


class BasicResponse(BaseModel):
    success: bool
    message: str
    deleted_faces: Optional[int] = None
    deleted_records: Optional[int] = None
    errors: Optional[List[str]] = None


class DeleteImagesRequest(BaseModel):
    image_paths: List[str]


@face_search_router.post(
    "/index",
    response_model=IndexResponse,
    status_code=status.HTTP_200_OK,
    summary="Index a face image",
    description="Index a single face image into the face search database.",
)
async def index_image(
    file: UploadFile = File(...),
):
    # 将上传文件保存到临时路径，再交给服务处理
    import tempfile
    import os

    suffix = ""
    filename = file.filename or "uploaded"
    _, ext = os.path.splitext(filename)
    if ext:
        suffix = ext

    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            content = await file.read()
            f.write(content)

        processed, total_faces, errors = _face_service.add_images([tmp_path])

        if processed == 0 and not errors:
            return IndexResponse(
                success=False,
                processed_images=0,
                total_faces=0,
                errors=["未检测到有效人脸或文件已存在索引中。"],
                message="未检测到有效人脸或文件已存在索引中。",
            )

        return IndexResponse(
            success=True,
            processed_images=processed,
            total_faces=total_faces,
            errors=errors,
            message="已入库。" if processed > 0 else "处理完成。",
        )
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


@face_search_router.post(
    "/query",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search similar faces by image",
    description="Search the face database using an uploaded image.",
)
async def search_by_image(
    file: UploadFile = File(...),
    top_k: int = Form(5),
    score_threshold: float = Form(0.8),
):
    import tempfile
    import os

    fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
    try:
        with os.fdopen(fd, "wb") as f:
            content = await file.read()
            f.write(content)

        try:
            ranked = _face_service.search_by_image_with_scores(
                query_image_path=tmp_path,
                top_k=top_k,
                max_distance=score_threshold,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc))

        matches: List[SearchMatch] = []
        for path, dist in ranked:
            matches.append(
                SearchMatch(image_path=path, distance=float(dist), original_path=None)
            )

        return SearchResponse(success=True, matches=matches)
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


@face_search_router.get(
    "/stats",
    response_model=StatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get face search statistics",
)
async def get_stats() -> StatsResponse:
    stats = _face_service.get_statistics()
    return StatsResponse(
        total_faces=stats.get("total_faces", 0),
        total_images=stats.get("total_images", 0),
        total_indexed_files=stats.get("total_indexed_files", 0),
    )


@face_search_router.post(
    "/reset",
    response_model=BasicResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset face database",
)
async def reset_database(payload: ResetRequest) -> BasicResponse:
    if not payload.confirm:
        return BasicResponse(success=False, message="请显式确认 confirm=true 以执行清空操作。")
    ok = _face_service.clear_database()
    return BasicResponse(success=ok, message="人脸数据库已清空。" if ok else "清空数据库失败。")


@face_search_router.post(
    "/delete-images",
    response_model=BasicResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete faces for given images",
)
async def delete_images(payload: DeleteImagesRequest) -> BasicResponse:
    deleted, errors = _face_service.delete_images(payload.image_paths)
    return BasicResponse(
        success=True,
        message="删除完成。",
        deleted_faces=deleted,
        errors=errors or [],
    )


@face_search_router.post(
    "/cleanup-orphans",
    response_model=BasicResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove orphaned records",
)
async def cleanup_orphans() -> BasicResponse:
    deleted, errors = _face_service.remove_orphaned_entries()
    return BasicResponse(
        success=True,
        message="孤儿记录清理完成。",
        deleted_records=deleted,
        errors=errors or [],
    )
