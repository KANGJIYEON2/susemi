"""Phase 4-4 의존성 그래프 / ripple-effect 엔드포인트."""

from fastapi import APIRouter, HTTPException, Query

from app.schemas.dependencies_schema import (
    FieldsResponse,
    GraphResponse,
    RippleResponse,
)
from app.services import dependencies


router = APIRouter()


@router.get("/ripple/fields", response_model=FieldsResponse)
def list_fields_endpoint():
    return FieldsResponse(fields=dependencies.list_fields())


@router.get("/ripple/graph", response_model=GraphResponse)
def graph_endpoint(year: int = Query(default=2025)):
    return dependencies.build_graph(year=year)


@router.get("/ripple/{field}", response_model=RippleResponse)
def ripple_endpoint(field: str, year: int = Query(default=2025)):
    if not field:
        raise HTTPException(status_code=400, detail="field 필수")
    return dependencies.ripple(field, year=year)
