"""
Authentication router for admin login/logout.
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Admin
from app.schemas import LoginRequest, LoginResponse, AdminResponse, AdminCreate
from app.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    get_token_username
)
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/admin", tags=["authentication"])
security = HTTPBearer()


@router.post("/register", response_model=AdminResponse, status_code=status.HTTP_201_CREATED)
def register(
    admin_data: AdminCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new admin user.

    Args:
        admin_data: Admin registration data (username, password)
        db: Database session

    Returns:
        AdminResponse: Created admin user

    Raises:
        HTTPException: If username already exists
    """
    # Check if admin already exists
    existing = db.query(Admin).filter(Admin.username == admin_data.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Create new admin
    admin = Admin(
        username=admin_data.username,
        password_hash=get_password_hash(admin_data.password)
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    return admin


@router.post("/login", response_model=LoginResponse)
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Admin login endpoint.

    Args:
        credentials: Login credentials (username, password)
        db: Database session

    Returns:
        LoginResponse: JWT access token and user info

    Raises:
        HTTPException: If credentials are invalid
    """
    # Find admin by username
    admin = db.query(Admin).filter(Admin.username == credentials.username).first()

    # Verify admin exists and password is correct
    if not admin or not verify_password(credentials.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": admin.username},
        expires_delta=access_token_expires
    )

    return LoginResponse(
        access_token=access_token,
        username=admin.username
    )


@router.post("/logout")
def logout():
    """
    Admin logout endpoint.

    Note: In a stateless JWT system, logout is handled client-side
    by deleting the token. This endpoint exists for API completeness
    and potential future session management.
    """
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=AdminResponse)
def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Get current admin information from JWT token.

    Args:
        credentials: HTTP Bearer credentials
        db: Database session

    Returns:
        AdminResponse: Current admin information

    Raises:
        HTTPException: If token is invalid or admin not found
    """
    token = credentials.credentials
    username = get_token_username(token)

    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    admin = db.query(Admin).filter(Admin.username == username).first()
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return admin


# Dependency for protected routes
def get_current_admin_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Admin | None:
    """
    Optional dependency that tries to get current admin but returns None if not authenticated.
    Useful for routes that have different behavior for authenticated vs non-authenticated users.
    """
    try:
        token = credentials.credentials
        username = get_token_username(token)
        if username:
            return db.query(Admin).filter(Admin.username == username).first()
    except Exception:
        pass
    return None


def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Admin:
    """
    Dependency for routes that require authentication.

    Args:
        credentials: HTTP Bearer credentials
        db: Database session

    Returns:
        Admin: The authenticated admin user

    Raises:
        HTTPException: If not authenticated
    """
    token = credentials.credentials
    username = get_token_username(token)

    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    admin = db.query(Admin).filter(Admin.username == username).first()
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return admin
