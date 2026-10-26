from __future__ import annotations

from enum import Enum
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.device import Device
from app.models.floor import Floor
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


# ----------------------------------------------------------------------
# Roles & Permissions Specification
# ----------------------------------------------------------------------

class Role(str, Enum):
    OPERATOR = "operator"
    SHIFT_INCHARGE = "shift_incharge"
    ELECTRICAL_ENGINEER = "electrical_engineer"
    MANAGEMENT = "management"
    TECHNICIAN = "technician"
    ADMIN = "admin"


class Permission(str, Enum):
    # Telemetry & Monitoring
    VIEW_TELEMETRY = "telemetry:view"
    INGEST_TELEMETRY = "telemetry:ingest"

    # Alarms & Faults
    VIEW_FAULTS = "faults:view"
    ACKNOWLEDGE_FAULTS = "faults:acknowledge"
    RECTIFY_FAULTS = "faults:rectify"

    # Maintenance & Work Orders
    VIEW_WORK_ORDERS = "work_orders:view"
    CREATE_WORK_ORDERS = "work_orders:create"
    ASSIGN_WORK_ORDERS = "work_orders:assign"
    LOG_WORK_ATTEMPTS = "work_orders:log_attempts"
    UPDATE_WORK_ORDER_STATUS = "work_orders:update_status"

    # Relays & Control
    VIEW_RELAYS = "relays:view"
    CONTROL_RELAYS = "relays:control"

    # Campus & Device Registry
    VIEW_CAMPUS = "campus:view"
    MANAGE_CAMPUS = "campus:manage"
    VIEW_DEVICES = "devices:view"
    MANAGE_DEVICES = "devices:manage"

    # Notifications & Audit
    VIEW_NOTIFICATIONS = "notifications:view"
    MANAGE_NOTIFICATIONS = "notifications:manage"
    VIEW_AUDIT_LOGS = "audit:view"

    # Administrative & Management
    MANAGE_USERS = "users:manage"
    VIEW_MANAGEMENT_REPORTS = "reports:view"
    SYSTEM_CONFIG = "system:config"


ROLE_ALIASES: dict[str, Role] = {
    "operator": Role.OPERATOR,
    "shift_incharge": Role.SHIFT_INCHARGE,
    "shift_in_charge": Role.SHIFT_INCHARGE,
    "shift-in-charge": Role.SHIFT_INCHARGE,
    "shift in charge": Role.SHIFT_INCHARGE,
    "electrical_engineer": Role.ELECTRICAL_ENGINEER,
    "electrical-engineer": Role.ELECTRICAL_ENGINEER,
    "electrical engineer": Role.ELECTRICAL_ENGINEER,
    "engineer": Role.ELECTRICAL_ENGINEER,
    "management": Role.MANAGEMENT,
    "manager": Role.MANAGEMENT,
    "technician": Role.TECHNICIAN,
    "tech": Role.TECHNICIAN,
    "maintenance": Role.TECHNICIAN,
    "admin": Role.ADMIN,
    "administrator": Role.ADMIN,
}


def normalize_role(role_raw: str | None) -> Role | None:
    if not role_raw:
        return None
    cleaned = role_raw.strip().lower()
    return ROLE_ALIASES.get(cleaned)


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.OPERATOR: {
        Permission.VIEW_TELEMETRY,
        Permission.VIEW_FAULTS,
        Permission.VIEW_RELAYS,
        Permission.VIEW_CAMPUS,
        Permission.VIEW_DEVICES,
        Permission.VIEW_NOTIFICATIONS,
        Permission.MANAGE_NOTIFICATIONS,
    },
    Role.SHIFT_INCHARGE: {
        Permission.VIEW_TELEMETRY,
        Permission.VIEW_FAULTS,
        Permission.ACKNOWLEDGE_FAULTS,
        Permission.VIEW_WORK_ORDERS,
        Permission.CREATE_WORK_ORDERS,
        Permission.ASSIGN_WORK_ORDERS,
        Permission.VIEW_RELAYS,
        Permission.VIEW_CAMPUS,
        Permission.VIEW_DEVICES,
        Permission.VIEW_NOTIFICATIONS,
        Permission.MANAGE_NOTIFICATIONS,
        Permission.VIEW_MANAGEMENT_REPORTS,
    },
    Role.ELECTRICAL_ENGINEER: {
        Permission.VIEW_TELEMETRY,
        Permission.VIEW_FAULTS,
        Permission.ACKNOWLEDGE_FAULTS,
        Permission.RECTIFY_FAULTS,
        Permission.VIEW_WORK_ORDERS,
        Permission.CREATE_WORK_ORDERS,
        Permission.ASSIGN_WORK_ORDERS,
        Permission.LOG_WORK_ATTEMPTS,
        Permission.UPDATE_WORK_ORDER_STATUS,
        Permission.VIEW_RELAYS,
        Permission.VIEW_CAMPUS,
        Permission.VIEW_DEVICES,
        Permission.VIEW_NOTIFICATIONS,
        Permission.MANAGE_NOTIFICATIONS,
        Permission.VIEW_MANAGEMENT_REPORTS,
    },
    Role.MANAGEMENT: {
        Permission.VIEW_TELEMETRY,
        Permission.VIEW_FAULTS,
        Permission.VIEW_WORK_ORDERS,
        Permission.VIEW_RELAYS,
        Permission.VIEW_CAMPUS,
        Permission.VIEW_DEVICES,
        Permission.VIEW_NOTIFICATIONS,
        Permission.MANAGE_NOTIFICATIONS,
        Permission.VIEW_MANAGEMENT_REPORTS,
    },
    Role.TECHNICIAN: {
        Permission.VIEW_TELEMETRY,
        Permission.VIEW_FAULTS,
        Permission.RECTIFY_FAULTS,
        Permission.VIEW_WORK_ORDERS,
        Permission.LOG_WORK_ATTEMPTS,
        Permission.UPDATE_WORK_ORDER_STATUS,
        Permission.VIEW_RELAYS,
        Permission.VIEW_CAMPUS,
        Permission.VIEW_DEVICES,
        Permission.VIEW_NOTIFICATIONS,
        Permission.MANAGE_NOTIFICATIONS,
    },
    Role.ADMIN: {
        perm for perm in Permission
    },
}


def has_permission(user_role: str | None, permission: Permission) -> bool:
    norm_role = normalize_role(user_role)
    if norm_role is None:
        return False
    return permission in ROLE_PERMISSIONS.get(norm_role, set())


# ----------------------------------------------------------------------
# Password Hashing & JWT Utilities
# ----------------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000,
    ).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000,
    ).hex()
    return secrets.compare_digest(candidate, digest)


def create_access_token(
    username: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    if expires_delta is not None:
        expires = datetime.now(timezone.utc) + expires_delta
    else:
        expires = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

    norm_role = normalize_role(role)
    role_str = norm_role.value if norm_role else role

    return jwt.encode(
        {"sub": username, "role": role_str, "exp": expires},
        settings.JWT_SECRET,
        algorithm="HS256",
    )


# ----------------------------------------------------------------------
# User Identity Dependencies
# ----------------------------------------------------------------------

def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not settings.AUTH_ENABLED:
        admin = db.query(User).filter(User.role == "admin").first()
        if admin:
            return admin
        return User(id=1, username="dev-admin", role="admin", is_active=True, created_at=datetime.now(timezone.utc))

    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            creds.credentials,
            settings.JWT_SECRET,
            algorithms=["HS256"],
        )
        username = payload.get("sub")
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_optional_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    if not settings.AUTH_ENABLED or creds is None:
        return None
    if creds.scheme.lower() != "bearer":
        return None
    try:
        payload = jwt.decode(
            creds.credentials,
            settings.JWT_SECRET,
            algorithms=["HS256"],
        )
        username = payload.get("sub")
        if not username:
            return None
        user = db.query(User).filter(User.username == username).first()
        if user and user.is_active:
            return user
    except JWTError:
        return None
    return None


# ----------------------------------------------------------------------
# Permission & Role Guards (Fail-Closed)
# ----------------------------------------------------------------------

def require_permission(permission: Permission):
    def permission_checker(user: User = Depends(get_current_user)) -> User:
        norm_role = normalize_role(user.role)
        if norm_role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unknown or missing role '{user.role}'. Access denied.",
            )
        if not has_permission(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: role '{user.role}' lacks '{permission.value}' permission.",
            )
        return user

    return permission_checker


def require_roles(*allowed_roles: str):
    normalized_allowed = {
        normalize_role(r).value
        for r in allowed_roles
        if normalize_role(r) is not None
    }

    def role_checker(user: User = Depends(get_current_user)) -> User:
        norm_user_role = normalize_role(user.role)
        if norm_user_role is None or norm_user_role.value not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for role '{user.role}'. Required: {', '.join(allowed_roles)}",
            )
        return user

    return role_checker


require_admin = require_roles("admin")
require_technician_or_admin = require_roles("technician", "electrical_engineer", "admin")
require_shift_incharge_or_admin = require_roles("shift_incharge", "electrical_engineer", "admin")
require_any_authenticated = get_current_user


# ----------------------------------------------------------------------
# Location Scope Verification
# ----------------------------------------------------------------------

def check_device_location_scope(user: User, device: Device, db: Session) -> bool:
    norm_role = normalize_role(user.role)
    if norm_role in (Role.ADMIN, Role.MANAGEMENT):
        return True

    # If user has no specific location constraint assigned, allow
    if user.assigned_block_id is None and user.assigned_floor_id is None:
        return True

    # Check floor scope constraint
    if user.assigned_floor_id is not None:
        if device.floor_id != user.assigned_floor_id:
            return False

    # Check block scope constraint
    if user.assigned_block_id is not None:
        if device.floor_id is None:
            return False
        floor = db.get(Floor, device.floor_id)
        if floor is None or floor.block_id != user.assigned_block_id:
            return False

    return True


def validate_device_access(
    device_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Device:
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    if not check_device_location_scope(user, device, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Device #{device_id} is outside authorized operational location scope.",
        )
    return device


# ----------------------------------------------------------------------
# Telemetry Ingestion Authentication
# ----------------------------------------------------------------------

def require_ingest(
    x_ingest_key: str | None = Header(default=None, alias="X-Ingest-Key"),
    user: User | None = Depends(get_optional_current_user),
) -> str:
    """
    Explicit, secure authentication path for device telemetry ingestion.
    Allows either:
    1. A valid X-Ingest-Key matching settings.INGEST_API_KEY (device authentication).
    2. An authenticated user (operator, technician, engineer, or admin) via Bearer token.
    """
    if not settings.AUTH_ENABLED:
        return "anonymous"

    # Path 1: Device authentication via X-Ingest-Key
    if settings.INGEST_API_KEY:
        if x_ingest_key:
            if secrets.compare_digest(x_ingest_key, settings.INGEST_API_KEY):
                return "device"
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid device ingestion key",
            )

    # Path 2: User authentication via Bearer token
    if user is not None:
        return user.username

    # Missing credentials
    if settings.INGEST_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid device ingestion key (X-Ingest-Key) or authenticated bearer token required",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for telemetry ingestion",
        )


def actor_name(user: User | None, fallback: str = "system") -> str:
    if user is None:
        return fallback
    return user.username


# ----------------------------------------------------------------------
# Initial Admin Provisioning
# ----------------------------------------------------------------------

INSECURE_ADMIN_PASSWORDS = {
    "admin",
    "password",
    "123456",
    "admin123",
    "secret",
    "root",
    "toor",
    "pass",
    "changeme",
}


def ensure_initial_admin(db: Session) -> User | None:
    admin = db.query(User).filter(User.role == "admin").first()
    if admin is not None:
        return admin

    username = (settings.ADMIN_USERNAME or "").strip()
    password = (settings.ADMIN_PASSWORD or "").strip()

    if not username:
        raise ValueError(
            "Initial administrator provisioning failed: ADMIN_USERNAME is missing or empty in environment."
        )
    if not password:
        raise ValueError(
            "Initial administrator provisioning failed: ADMIN_PASSWORD is missing or empty in environment."
        )

    if len(password) < 8:
        raise ValueError(
            "Initial administrator provisioning failed: ADMIN_PASSWORD must be at least 8 characters."
        )

    if password.lower() in INSECURE_ADMIN_PASSWORDS:
        raise ValueError(
            "Initial administrator provisioning failed: ADMIN_PASSWORD uses a known insecure or default credential."
        )

    if username.lower() == password.lower():
        raise ValueError(
            "Initial administrator provisioning failed: ADMIN_PASSWORD cannot be identical to ADMIN_USERNAME."
        )

    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user is not None:
        raise ValueError(
            f"Cannot provision initial admin: username '{username}' already exists with role '{existing_user.role}'."
        )

    admin = User(
        username=username,
        password_hash=hash_password(password),
        role="admin",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin
