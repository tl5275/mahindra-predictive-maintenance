"""Fleet snapshot endpoints backed by Redis latest-state reads."""

from __future__ import annotations

from fastapi import APIRouter, Query

from core.config import get_settings
from services.state_service import fleet_state_service


router = APIRouter(tags=["Fleet"])
settings = get_settings()


@router.get("/fleet")
def get_fleet(
    limit: int = Query(default=settings.fleet_page_default, ge=1, le=settings.fleet_page_max),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> dict:
    return fleet_state_service.get_fleet_page(
        limit=limit,
        offset=offset,
        search=search,
        status=status,
    )
