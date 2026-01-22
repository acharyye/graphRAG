"""Authentication API routes."""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from src.api.dependencies import (
    CurrentUser,
    Neo4jDep,
    SettingsDep,
    create_access_token,
    hash_password,
    verify_password,
)
from src.api.models import (
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    UserCreate,
    UserResponse,
    UserRole,
)
from src.graph.ingest import DataIngester

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    settings: SettingsDep,
    neo4j: Neo4jDep,
) -> LoginResponse:
    """Authenticate user and return access token."""
    # Find user by email
    result = neo4j.execute_query(
        "MATCH (u:User {email: $email}) RETURN u",
        {"email": request.email},
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user_data = result[0]["u"]

    # Verify password
    if not verify_password(request.password, user_data["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Create access token
    token = create_access_token(
        user_id=user_data["id"],
        email=user_data["email"],
        role=UserRole(user_data["role"]),
        client_ids=user_data.get("client_ids", []),
        settings=settings,
    )

    user = UserResponse(
        id=user_data["id"],
        email=user_data["email"],
        name=user_data["name"],
        role=UserRole(user_data["role"]),
        client_ids=user_data.get("client_ids", []),
        created_at=user_data.get("created_at", datetime.utcnow()),
        updated_at=user_data.get("updated_at", datetime.utcnow()),
    )

    logger.info(f"User logged in: {user.email}")

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRATION_HOURS * 3600,
        user=user,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserCreate,
    neo4j: Neo4jDep,
) -> UserResponse:
    """Register a new user (admin only in production)."""
    # Check if email already exists
    existing = neo4j.execute_query(
        "MATCH (u:User {email: $email}) RETURN u",
        {"email": request.email},
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Hash password and create user
    hashed = hash_password(request.password)
    user_data = {
        "email": request.email,
        "hashed_password": hashed,
        "name": request.name,
        "role": request.role.value,
        "client_ids": request.client_ids,
    }

    ingester = DataIngester(neo4j)
    user_id = ingester.ingest_user(user_data)

    # Fetch created user
    result = neo4j.execute_query(
        "MATCH (u:User {id: $id}) RETURN u",
        {"id": user_id},
    )

    user_data = result[0]["u"]

    logger.info(f"User registered: {request.email}")

    return UserResponse(
        id=user_data["id"],
        email=user_data["email"],
        name=user_data["name"],
        role=UserRole(user_data["role"]),
        client_ids=user_data.get("client_ids", []),
        created_at=user_data.get("created_at", datetime.utcnow()),
        updated_at=user_data.get("updated_at", datetime.utcnow()),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser) -> UserResponse:
    """Get current user information."""
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request: PasswordChangeRequest,
    current_user: CurrentUser,
    neo4j: Neo4jDep,
) -> None:
    """Change current user's password."""
    # Fetch user with password
    result = neo4j.execute_query(
        "MATCH (u:User {id: $id}) RETURN u",
        {"id": current_user.id},
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user_data = result[0]["u"]

    # Verify current password
    if not verify_password(request.current_password, user_data["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    new_hashed = hash_password(request.new_password)
    neo4j.execute_write(
        """
        MATCH (u:User {id: $id})
        SET u.hashed_password = $hashed_password,
            u.updated_at = datetime()
        """,
        {"id": current_user.id, "hashed_password": new_hashed},
    )

    logger.info(f"Password changed for user: {current_user.email}")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user: CurrentUser) -> None:
    """Logout current user (client-side token invalidation)."""
    # In a production system, you might:
    # - Add token to a blacklist
    # - Track active sessions
    # For MVP, logout is handled client-side by discarding the token
    logger.info(f"User logged out: {current_user.email}")
