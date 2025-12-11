from typing import List, Optional

from fastapi import APIRouter, status
from pydantic import BaseModel

from core.config import (
    DEFAULT_AUTH_DB_PATH,
    DEFAULT_ADMIN_USERNAME,
    DEFAULT_ADMIN_PASSWORD,
)
from services.auth.service import AuthService


auth_router = APIRouter(prefix="/auth", tags=["Auth"])


# Initialize AuthService using the same defaults as Gradio App
_auth_service = AuthService(
    db_path=DEFAULT_AUTH_DB_PATH,
    default_admin_username=DEFAULT_ADMIN_USERNAME,
    default_admin_password=DEFAULT_ADMIN_PASSWORD,
)
_auth_service.init_db()


class RegisterRequest(BaseModel):
    username: str
    password: str


class BasicResponse(BaseModel):
    success: bool
    message: str


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BasicResponse):
    role: Optional[str] = None


class ApproveRequest(BaseModel):
    username: str


class PendingUsersResponse(BaseModel):
    pending: List[str]


class UserItem(BaseModel):
    username: str
    role: str
    status: str


class UsersResponse(BaseModel):
    users: List[UserItem]


class AdminChangeRequest(BaseModel):
    target_username: str
    current_username: str


@auth_router.post(
    "/register",
    response_model=BasicResponse,
    status_code=status.HTTP_200_OK,
    summary="User registration",
    description="Register a new user; the user will be pending until approved by admin.",
)
async def register_user(payload: RegisterRequest) -> BasicResponse:
    success, message = _auth_service.register_user(payload.username, payload.password)
    return BasicResponse(success=success, message=message)


@auth_router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Login with username and password; returns role if success.",
)
async def login_user(payload: LoginRequest) -> LoginResponse:
    success, role, message = _auth_service.login_user(payload.username, payload.password)
    # When login fails, role will be None according to AuthService implementation
    return LoginResponse(success=success, role=role, message=message)


@auth_router.get(
    "/pending",
    response_model=PendingUsersResponse,
    status_code=status.HTTP_200_OK,
    summary="Get pending users",
    description="Get usernames of users waiting for admin approval.",
)
async def get_pending_users() -> PendingUsersResponse:
    pending = _auth_service.get_pending_users()
    return PendingUsersResponse(pending=pending)


@auth_router.post(
    "/approve",
    response_model=BasicResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve user",
    description="Approve a pending user.",
)
async def approve_user(payload: ApproveRequest) -> BasicResponse:
    success, message = _auth_service.approve_user(payload.username)
    return BasicResponse(success=success, message=message)


@auth_router.get(
    "/users",
    response_model=UsersResponse,
    status_code=status.HTTP_200_OK,
    summary="Get users list",
    description="Get all users except the default admin account.",
)
async def get_all_users() -> UsersResponse:
    users_raw = _auth_service.get_all_users()
    users = [UserItem(**u) for u in users_raw]
    return UsersResponse(users=users)


@auth_router.post(
    "/grant-admin",
    response_model=BasicResponse,
    status_code=status.HTTP_200_OK,
    summary="Grant admin role",
    description="Grant admin role to a target user (only default admin can operate).",
)
async def grant_admin(payload: AdminChangeRequest) -> BasicResponse:
    success, message = _auth_service.grant_admin_role(
        target_username=payload.target_username,
        current_username=payload.current_username,
    )
    return BasicResponse(success=success, message=message)


@auth_router.post(
    "/revoke-admin",
    response_model=BasicResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke admin role",
    description="Revoke admin role from a target user (only default admin can operate).",
)
async def revoke_admin(payload: AdminChangeRequest) -> BasicResponse:
    success, message = _auth_service.revoke_admin_role(
        target_username=payload.target_username,
        current_username=payload.current_username,
    )
    return BasicResponse(success=success, message=message)
