"""Read access to the mapping registry — which CSV shapes the system
recognizes and exactly how each one maps into the canonical table."""

from fastapi import APIRouter
from sqlmodel import select

from app.core.db_dep import DbSession
from app.models.mapping_function import MappingFunction
from app.schemas.mapping_function import MappingFunctionOut

router = APIRouter()


@router.get("", response_model=list[MappingFunctionOut], operation_id="list_mapping_functions")
async def list_mapping_functions(session: DbSession) -> list[MappingFunctionOut]:
    rows = (
        (await session.execute(select(MappingFunction).order_by(MappingFunction.created_at)))
        .scalars()
        .all()
    )
    return [MappingFunctionOut(**m.model_dump()) for m in rows]
