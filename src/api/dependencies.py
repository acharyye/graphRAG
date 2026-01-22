"""FastAPI dependency injection."""

import logging
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from config.settings import Settings, get_settings
from src.graph.client import Neo4jClient, get_neo4j_client
from src.rag.engine import GraphRAGEngine, get_graphrag_engine

from .models import TokenPayload, UserResponse, UserRole

logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_settings_dep() -> Settings:
    """Dependency for settings."""
    return get_settings()


def get_neo4j_dep() -> Neo4jClient:
    """Dependency for Neo4j client."""
    return get_neo4j_client()


def get_graphrag_dep() -> GraphRAGEngine:
    """Dependency for GraphRAG engine."""
    return get_graphrag_engine()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(
    user_id: str,
    email: str,
    role: UserRole,
    client_ids: list[str],
    settings: Settings,
) -> str:
    """Create a JWT access token.

    Args:
        user_id: User identifier.
        email: User email.
        role: User role.
        client_ids: Accessible client IDs.
        settings: Application settings.

    Returns:
        Encoded JWT token.
    """
    expires = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role.value,
        "client_ids": client_ids,
        "exp": expires,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, settings: Settings) -> TokenPayload:
    """Decode and validate a JWT token.

    Args:
        token: JWT token string.
        settings: Application settings.

    Returns:
        Decoded token payload.

    Raises:
        HTTPException: If token is invalid.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return TokenPayload(
            sub=payload["sub"],
            email=payload["email"],
            role=UserRole(payload["role"]),
            client_ids=payload["client_ids"],
            exp=datetime.fromtimestamp(payload["exp"]),
        )
    except JWTError as e:
        logger.warning(f"Invalid token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    settings: Annotated[Settings, Depends(get_settings_dep)],
    neo4j: Annotated[Neo4jClient, Depends(get_neo4j_dep)],
) -> UserResponse:
    """Get the current authenticated user.

    Args:
        credentials: Bearer token credentials.
        settings: Application settings.
        neo4j: Neo4j client.

    Returns:
        Current user.

    Raises:
        HTTPException: If authentication fails.
    """
    token_payload = decode_token(credentials.credentials, settings)

    # Verify user exists
    result = neo4j.execute_query(
        "MATCH (u:User {id: $user_id}) RETURN u",
        {"user_id": token_payload.sub},
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    user_data = result[0]["u"]
    return UserResponse(
        id=user_data["id"],
        email=user_data["email"],
        name=user_data["name"],
        role=UserRole(user_data["role"]),
        client_ids=user_data.get("client_ids", []),
        created_at=user_data.get("created_at", datetime.utcnow()),
        updated_at=user_data.get("updated_at", datetime.utcnow()),
    )


async def get_current_active_user(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> UserResponse:
    """Get current active user (same as get_current_user for now)."""
    return current_user


def require_role(*roles: UserRole):
    """Dependency factory to require specific roles.

    Args:
        roles: Allowed roles.

    Returns:
        Dependency function.
    """

    async def role_checker(
        current_user: Annotated[UserResponse, Depends(get_current_user)],
    ) -> UserResponse:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {current_user.role} not authorized for this action",
            )
        return current_user

    return role_checker


def require_client_access(client_id: str):
    """Dependency factory to require access to a specific client.

    Args:
        client_id: Client ID to check access for.

    Returns:
        Dependency function.
    """

    async def client_checker(
        current_user: Annotated[UserResponse, Depends(get_current_user)],
    ) -> UserResponse:
        if current_user.role == UserRole.ADMIN:
            return current_user

        if client_id not in current_user.client_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied for this client",
            )
        return current_user

    return client_checker


async def verify_client_access(
    client_id: str,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> bool:
    """Verify user has access to a client.

    Args:
        client_id: Client ID to check.
        current_user: Current user.

    Returns:
        True if access is allowed.

    Raises:
        HTTPException: If access denied.
    """
    if current_user.role == UserRole.ADMIN:
        return True

    if client_id not in current_user.client_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied for this client",
        )
    return True


# Type aliases for common dependencies
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
Neo4jDep = Annotated[Neo4jClient, Depends(get_neo4j_dep)]
GraphRAGDep = Annotated[GraphRAGEngine, Depends(get_graphrag_dep)]
CurrentUser = Annotated[UserResponse, Depends(get_current_user)]
AdminUser = Annotated[UserResponse, Depends(require_role(UserRole.ADMIN))]
AnalystUser = Annotated[UserResponse, Depends(require_role(UserRole.ADMIN, UserRole.ANALYST))]
