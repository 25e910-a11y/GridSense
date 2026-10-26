from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import (
    Permission,
    Role,
    ROLE_PERMISSIONS,
    create_access_token,
    get_current_user,
    get_optional_current_user,
    hash_password,
    normalize_role,
    require_admin,
    verify_password,
)
from app.db.database import get_db
from app.models.block import Block
from app.models.floor import Floor
from app.models.user import User
from app.services.audit import write_audit

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=6, max_length=200)
    role: str = "operator"
    assigned_block_id: int | None = None
    assigned_floor_id: int | None = None


class UserUpdateRequest(BaseModel):
    role: str | None = None
    assigned_block_id: int | None = None
    assigned_floor_id: int | None = None
    is_active: bool | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    norm_role = normalize_role(payload.role)
    if norm_role is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{payload.role}'. Must be one of: operator, shift_incharge, electrical_engineer, management, technician, admin.",
        )

    # Security Rule: Only an authenticated administrator can provision privileged/staff roles.
    # Unauthenticated public registration may ONLY create an operator account.
    if norm_role != Role.OPERATOR:
        if current_user is None:
            if norm_role == Role.ADMIN:
                detail_msg = "Public registration cannot grant administrative privileges"
            elif norm_role == Role.TECHNICIAN:
                detail_msg = "Public registration cannot grant technician privileges; technician accounts must be provisioned by an administrator"
            else:
                detail_msg = f"Public registration cannot grant '{norm_role.value}' privileges; staff accounts must be provisioned by an administrator"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail_msg,
            )
        if normalize_role(current_user.role) != Role.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Only an administrator can provision users with role '{norm_role.value}'",
            )
        assigned_role = norm_role.value
    else:
        assigned_role = Role.OPERATOR.value

    # Validate location scoping foreign keys if provided
    if payload.assigned_block_id is not None:
        block = db.get(Block, payload.assigned_block_id)
        if not block:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned block not found")

    if payload.assigned_floor_id is not None:
        floor = db.get(Floor, payload.assigned_floor_id)
        if not floor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned floor not found")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=assigned_role,
        assigned_block_id=payload.assigned_block_id,
        assigned_floor_id=payload.assigned_floor_id,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    write_audit(
        db,
        actor=current_user.username if current_user else payload.username,
        action="register",
        entity_type="user",
        detail=f"Registered user with role '{assigned_role}'",
    )
    db.commit()
    db.refresh(user)

    return {
        "status": "success",
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "assigned_block_id": user.assigned_block_id,
        "assigned_floor_id": user.assigned_floor_id,
    }


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    norm_role = normalize_role(user.role)
    permissions = [p.value for p in ROLE_PERMISSIONS.get(norm_role, set())] if norm_role else []
    token = create_access_token(user.username, user.role)

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": norm_role.value if norm_role else user.role,
        "username": user.username,
        "assigned_block_id": user.assigned_block_id,
        "assigned_floor_id": user.assigned_floor_id,
        "permissions": permissions,
    }


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    norm_role = normalize_role(user.role)
    permissions = [p.value for p in ROLE_PERMISSIONS.get(norm_role, set())] if norm_role else []
    return {
        "authenticated": True,
        "id": user.id,
        "username": user.username,
        "role": norm_role.value if norm_role else user.role,
        "assigned_block_id": user.assigned_block_id,
        "assigned_floor_id": user.assigned_floor_id,
        "permissions": permissions,
    }


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    users = db.query(User).order_by(User.id).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "assigned_block_id": u.assigned_block_id,
            "assigned_floor_id": u.assigned_floor_id,
            "is_active": u.is_active,
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.role is not None:
        norm = normalize_role(payload.role)
        if norm is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role '{payload.role}'")
        user.role = norm.value

    if payload.assigned_block_id is not None:
        if payload.assigned_block_id > 0:
            block = db.get(Block, payload.assigned_block_id)
            if not block:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned block not found")
            user.assigned_block_id = payload.assigned_block_id
        else:
            user.assigned_block_id = None

    if payload.assigned_floor_id is not None:
        if payload.assigned_floor_id > 0:
            floor = db.get(Floor, payload.assigned_floor_id)
            if not floor:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned floor not found")
            user.assigned_floor_id = payload.assigned_floor_id
        else:
            user.assigned_floor_id = None

    if payload.is_active is not None:
        user.is_active = payload.is_active

    write_audit(
        db,
        actor=current_user.username,
        action="update_user",
        entity_type="user",
        entity_id=user.id,
        detail=f"Updated user '{user.username}' (role={user.role}, block={user.assigned_block_id})",
    )
    db.commit()
    db.refresh(user)

    return {
        "status": "success",
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "assigned_block_id": user.assigned_block_id,
        "assigned_floor_id": user.assigned_floor_id,
        "is_active": user.is_active,
    }
