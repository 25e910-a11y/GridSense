from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_admin
from app.db.database import get_db
from app.models.block import Block
from app.models.college import College
from app.models.floor import Floor
from app.models.user import User
from app.services.audit import write_audit

router = APIRouter(
    prefix="/locations",
    tags=["Locations"],
)


# --------------------------------------------------
# COLLEGE
# --------------------------------------------------

@router.post("/colleges")
def create_college(
    name: str,
    code: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing = db.query(College).filter(
        College.name == name
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="College already exists",
        )

    college = College(
        name=name,
        code=code,
    )

    db.add(college)
    db.flush()

    write_audit(
        db,
        actor=current_user.username,
        action="create_college",
        entity_type="college",
        entity_id=college.id,
        detail=f"Created college '{name}' ({code})",
    )

    db.commit()
    db.refresh(college)

    return {
        "status": "success",
        "message": "College created",
        "college_id": college.id,
    }


@router.get("/colleges")
def get_colleges(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(College).all()


# --------------------------------------------------
# BLOCK
# --------------------------------------------------

@router.post("/blocks")
def create_block(
    college_id: int,
    name: str,
    code: str | None = None,
    description: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    college = db.get(College, college_id)

    if college is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="College not found",
        )

    block = Block(
        college_id=college_id,
        name=name,
        code=code,
        description=description,
    )

    db.add(block)
    db.flush()

    write_audit(
        db,
        actor=current_user.username,
        action="create_block",
        entity_type="block",
        entity_id=block.id,
        detail=f"Created block '{name}' in college {college_id}",
    )

    db.commit()
    db.refresh(block)

    return {
        "status": "success",
        "message": "Block created",
        "block_id": block.id,
    }


@router.get("/blocks")
def get_blocks(
    college_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Block)

    if college_id is not None:
        query = query.filter(Block.college_id == college_id)

    # Enforce location scoping for assigned blocks
    if current_user.assigned_block_id is not None:
        query = query.filter(Block.id == current_user.assigned_block_id)

    return query.all()


# --------------------------------------------------
# FLOOR
# --------------------------------------------------

@router.post("/floors")
def create_floor(
    block_id: int,
    floor_number: int,
    name: str,
    description: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    block = db.get(Block, block_id)

    if block is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Block not found",
        )

    floor = Floor(
        block_id=block_id,
        floor_number=floor_number,
        name=name,
        description=description,
    )

    db.add(floor)
    db.flush()

    write_audit(
        db,
        actor=current_user.username,
        action="create_floor",
        entity_type="floor",
        entity_id=floor.id,
        detail=f"Created floor '{name}' (#{floor_number}) in block {block_id}",
    )

    db.commit()
    db.refresh(floor)

    return {
        "status": "success",
        "message": "Floor created",
        "floor_id": floor.id,
    }


@router.get("/floors")
def get_floors(
    block_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Floor)

    if block_id is not None:
        if current_user.assigned_block_id is not None and block_id != current_user.assigned_block_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Block #{block_id} is outside your authorized operational scope.",
            )
        query = query.filter(Floor.block_id == block_id)
    elif current_user.assigned_block_id is not None:
        query = query.filter(Floor.block_id == current_user.assigned_block_id)
    elif current_user.assigned_floor_id is not None:
        query = query.filter(Floor.id == current_user.assigned_floor_id)

    return query.all()
